package unitree4d;

import java.time.Duration;
import java.util.Locale;

/** Native-library-free Java 17 probe for Mac, Linux/companion, or roboRIO. */
public final class L2Probe {
  private L2Probe() {}
  public static void main(String[] args) throws Exception {
    if (args.length != 3) {
      System.err.println("Usage: L2Probe <local-bind-ip> <lidar-ip> <seconds>");
      System.exit(1);
    }
    double seconds = Double.parseDouble(args[2]);
    if (!Double.isFinite(seconds) || seconds <= 0) throw new IllegalArgumentException("Positive seconds required");
    try (var receiver = new L2Receiver(args[0], 6201, args[1], 6101)) {
      long start = System.nanoTime();
      while ((System.nanoTime() - start) * 1e-9 < seconds) {
        Thread.sleep(1000);
        var health = receiver.health();
        var scan = receiver.latestFresh(Duration.ofMillis(250));
        System.out.printf(Locale.ROOT,
            "scans=%d points=%d invalid=%d gaps=%d fresh=%s dirty=%.2f%n",
            health.validScans(), health.validPoints(), health.invalidPackets(),
            health.sequenceGaps(), scan.isPresent(), scan.map(s -> (double) s.dirtyIndex()).orElse(Double.NaN));
        if (!health.running()) throw new IllegalStateException(health.error());
      }
      var health = receiver.health();
      double elapsed = (System.nanoTime() - start) * 1e-9;
      System.out.printf(Locale.ROOT,
          "{\"duration_s\":%.3f,\"valid_scans\":%d,\"valid_points\":%d,\"points_per_s\":%.1f,"
          + "\"invalid_packets\":%d,\"sequence_gaps\":%d,\"discontinuities\":%d}%n",
          elapsed, health.validScans(), health.validPoints(), health.validPoints() / elapsed,
          health.invalidPackets(), health.sequenceGaps(), health.discontinuities());
      if (health.validScans() == 0 || health.invalidPackets() != 0 || health.sequenceGaps() != 0
          || receiver.latestFresh(Duration.ofMillis(250)).isEmpty()) System.exit(2);
    }
  }
}
