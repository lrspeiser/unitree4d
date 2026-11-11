package unitree4d;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.zip.CRC32;

/** Real packet/reference parity, corrupt input, UDP source and stale-data tests. */
public final class L2Tests {
  private static void check(boolean condition, String message) {
    if (!condition) throw new AssertionError(message);
  }
  private static void reject(byte[] data) {
    try {
      new L2PacketDecoder().decode(data, data.length, 123);
      throw new AssertionError("Malformed packet was accepted");
    } catch (IllegalArgumentException expected) { /* expected */ }
  }
  private static void checksum(byte[] data) {
    CRC32 crc = new CRC32(); crc.update(data, 12, data.length - 24);
    ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN).putInt(data.length - 12, (int) crc.getValue());
  }
  @SuppressWarnings("try") // Explicit close is part of the shutdown/port-release tests.
  public static void main(String[] args) throws Exception {
    byte[] packet = Files.readAllBytes(Path.of("tests/fixtures/l2-scan.bin"));
    var scan = new L2PacketDecoder().decode(packet, packet.length, 123);
    check(scan.receivedAtNanos() == 123, "Receive timestamp lost");
    var reference = Files.readAllLines(Path.of("build/reference.csv"));
    check(scan.pointCount() == reference.size() && scan.pointCount() > 0, "Point count differs from SDK");
    double maxDifference = 0;
    for (int i = 0; i < reference.size(); i++) {
      String[] values = reference.get(i).split(",");
      for (int j = 0; j < 4; j++) {
        double difference = Math.abs(scan.xyzi()[i * 4 + j] - Double.parseDouble(values[j]));
        if (j < 3) maxDifference = Math.max(maxDifference, difference);
        check(difference < (j < 3 ? 0.002 : 0.0001), "Official SDK coordinate mismatch");
      }
    }
    byte[] changed = packet.clone(); changed[0] ^= 1; reject(changed);
    changed = packet.clone(); changed[200] ^= 1; reject(changed);
    changed = java.util.Arrays.copyOf(packet, 1043); reject(changed);
    changed = packet.clone();
    ByteBuffer.wrap(changed).order(ByteOrder.LITTLE_ENDIAN).putInt(128, 301); checksum(changed); reject(changed);
    changed = packet.clone();
    ByteBuffer.wrap(changed).order(ByteOrder.LITTLE_ENDIAN).putFloat(92, Float.NaN); checksum(changed); reject(changed);
    changed = packet.clone();
    ByteBuffer.wrap(changed).order(ByteOrder.LITTLE_ENDIAN).putInt(24, 1_000_000_000); checksum(changed); reject(changed);
    changed = packet.clone();
    java.util.Arrays.fill(changed, 132, 732, (byte) 0); checksum(changed);
    check(new L2PacketDecoder().decode(changed, changed.length, 0).pointCount() == 0, "Zero ranges weren't excluded");

    // Use real UDP sockets; source-port filtering, corruption and silence must not refresh stale data.
    try (var sender = new DatagramSocket(0, InetAddress.getLoopbackAddress());
        var reservation = new DatagramSocket(0, InetAddress.getLoopbackAddress())) {
      int port = reservation.getLocalPort(); reservation.close();
      try (var receiver = new L2Receiver("127.0.0.1", port, "127.0.0.1", sender.getLocalPort())) {
        check(receiver.latestFresh(Duration.ofMillis(100)).isEmpty(), "Fresh before first packet");
        try (var wrongSource = new DatagramSocket()) {
          wrongSource.send(new DatagramPacket(packet, packet.length, InetAddress.getLoopbackAddress(), port));
        }
        Thread.sleep(30);
        check(receiver.latestFresh(Duration.ofMillis(100)).isEmpty(), "Wrong source accepted");
        sender.send(new DatagramPacket(packet, packet.length, InetAddress.getLoopbackAddress(), port));
        long deadline = System.nanoTime() + 1_000_000_000L;
        while (receiver.health().validScans() == 0 && System.nanoTime() < deadline) Thread.sleep(2);
        check(receiver.latestFresh(Duration.ofMillis(500)).isPresent(), "UDP frame not decoded");
        Thread.sleep(120);
        byte[] corrupt = packet.clone(); corrupt[300] ^= 1;
        sender.send(new DatagramPacket(corrupt, corrupt.length, InetAddress.getLoopbackAddress(), port));
        Thread.sleep(30);
        check(receiver.latestFresh(Duration.ofMillis(100)).isEmpty(), "Silence/corruption refreshed stale data");
        check(receiver.health().invalidPackets() == 1, "Bad CRC not counted");
        check(receiver.health().validScans() == 1, "Invalid/source-filtered packet accepted");
        receiver.close();
        check(!receiver.health().running(), "Worker did not stop");
        check(receiver.latestFresh(Duration.ofSeconds(30)).isEmpty(), "Closed receiver reports fresh data");
      }
    }
    System.out.printf("PASS: SDK parity (%d points, max error %.7f m), corruption, source filter, stale data, shutdown%n",
        scan.pointCount(), maxDifference);
  }
}
