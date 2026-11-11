package unitree4d;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/** Background receive-only reader. One latest slice is retained; no unbounded queue. */
public final class L2Receiver implements AutoCloseable {
  public record Health(long validScans, long validPoints, long invalidPackets,
      long otherPackets, long sequenceGaps, long discontinuities, boolean running, String error) {}

  private final DatagramSocket socket;
  private final InetAddress source;
  private final int sourcePort;
  private final Thread worker;
  private volatile boolean running = true;
  private volatile String error = "";
  private final AtomicReference<L2PacketDecoder.Scan> latest = new AtomicReference<>();
  private final AtomicLong scans = new AtomicLong(), points = new AtomicLong();
  private final AtomicLong invalid = new AtomicLong(), other = new AtomicLong();
  private final AtomicLong gaps = new AtomicLong(), discontinuities = new AtomicLong();

  public L2Receiver(String bindIp, int listenPort, String sourceIp, int sourcePort) throws IOException {
    this.source = InetAddress.getByName(sourceIp);
    this.sourcePort = sourcePort;
    DatagramSocket created = new DatagramSocket(null);
    try {
      created.setReceiveBufferSize(2 * 1024 * 1024);
      created.bind(new InetSocketAddress(InetAddress.getByName(bindIp), listenPort));
    } catch (IOException | RuntimeException e) {
      created.close();
      throw e;
    }
    socket = created;
    worker = new Thread(this::receive, "Unitree-L2-UDP");
    worker.setDaemon(true);
    worker.start();
  }

  private void receive() {
    byte[] buffer = new byte[65535];
    DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
    L2PacketDecoder decoder = new L2PacketDecoder();
    long previous = -1;
    try {
      while (running) {
        packet.setLength(buffer.length);
        socket.receive(packet);
        long receivedAt = System.nanoTime();
        if (!packet.getAddress().equals(source) || packet.getPort() != sourcePort) {
          other.incrementAndGet(); continue;
        }
        if (packet.getLength() >= 12
            && ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN).getInt(4) != 102) {
          other.incrementAndGet(); continue;
        }
        try {
          var scan = decoder.decode(buffer, packet.getLength(), receivedAt);
          if (previous >= 0) {
            long delta = (scan.sequence() - previous) & 0xffffffffL;
            if (previous <= 1023 && scan.sequence() <= 1023) {
              delta = (scan.sequence() - previous + 1024) % 1024;
            }
            if (delta > 1 && delta < 512) gaps.addAndGet(delta - 1);
            else if (delta != 1) discontinuities.incrementAndGet();
          }
          previous = scan.sequence();
          points.addAndGet(scan.pointCount());
          scans.incrementAndGet();
          latest.set(scan);
        } catch (IllegalArgumentException e) {
          invalid.incrementAndGet();
        }
      }
    } catch (SocketException e) {
      if (running) error = e.toString();
    } catch (IOException | RuntimeException e) {
      error = e.toString();
    } finally {
      running = false;
      socket.close();
    }
  }

  /** Ages use the receiver's monotonic clock, never the unsynchronised sensor clock. */
  public Optional<L2PacketDecoder.Scan> latestFresh(Duration maxAge) {
    if (maxAge.isNegative() || maxAge.isZero()) throw new IllegalArgumentException("Positive age required");
    var scan = latest.get();
    if (!running || scan == null) return Optional.empty();
    long age = System.nanoTime() - scan.receivedAtNanos();
    return age >= 0 && age <= maxAge.toNanos() ? Optional.of(scan) : Optional.empty();
  }

  public Health health() {
    return new Health(scans.get(), points.get(), invalid.get(), other.get(),
        gaps.get(), discontinuities.get(), running, error);
  }

  @Override public void close() {
    running = false;
    socket.close();
    try { worker.join(1000); }
    catch (InterruptedException e) { Thread.currentThread().interrupt(); }
  }
}
