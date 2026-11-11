package unitree4d;

import edu.wpi.first.networktables.DoubleArrayPublisher;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.NetworkTablesJNI;
import edu.wpi.first.networktables.PubSubOption;
import java.time.Duration;

/** Publishes one coherent, timestamped diagnostic sample at the caller's chosen rate. */
public final class L2Telemetry implements AutoCloseable {
  private final DoubleArrayPublisher sample;
  private final L2Receiver receiver;
  public L2Telemetry(NetworkTableInstance nt, L2Receiver receiver) {
    this.receiver = receiver;
    // Keep duplicate values so loss of the publisher can be detected by sample age.
    sample = nt.getTable("UnitreeL2").getDoubleArrayTopic("sample")
        .publish(PubSubOption.keepDuplicates(true), PubSubOption.periodic(0.1));
  }
  /** [fresh, sequence, pointCount, packetNearestReturnM, dirtyIndex, apdTempC, ageSeconds]. */
  public void periodic() {
    var scan = receiver.latestFresh(Duration.ofMillis(250));
    long now = NetworkTablesJNI.now();
    if (scan.isEmpty()) {
      sample.set(new double[] {0, -1, 0, Double.NaN, Double.NaN, Double.NaN, Double.NaN}, now);
      return;
    }
    var s = scan.get();
    double range = s.nearestReturnMeters();
    sample.set(new double[] {1, s.sequence(), s.pointCount(),
        Double.isFinite(range) ? range : Double.NaN, s.dirtyIndex(), s.apdTemperatureC(),
        s.ageSeconds(System.nanoTime())}, now);
  }
  @Override public void close() { sample.close(); }
}
