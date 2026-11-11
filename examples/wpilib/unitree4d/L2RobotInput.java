package unitree4d;

import edu.wpi.first.networktables.DoubleArraySubscriber;
import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.NetworkTablesJNI;
import java.util.Optional;

/** roboRIO subscriber: rejects stale NT values even if the Jetson process died. */
public final class L2RobotInput implements AutoCloseable {
  private final DoubleArraySubscriber sample;
  public L2RobotInput(NetworkTableInstance nt) {
    sample = nt.getTable("UnitreeL2").getDoubleArrayTopic("sample").subscribe(new double[0]);
  }
  public Optional<double[]> latestFresh() {
    var value = sample.getAtomic();
    long elapsedUs = NetworkTablesJNI.now() - value.timestamp;
    if (value.timestamp == 0 || elapsedUs < 0 || elapsedUs > 300_000
        || value.value.length != 7 || value.value[0] != 1
        || !Double.isFinite(value.value[6]) || value.value[6] < 0
        || elapsedUs * 1e-6 + value.value[6] > 0.3) return Optional.empty();
    return Optional.of(value.value);
  }
  @Override public void close() { sample.close(); }
}
