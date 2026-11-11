package unitree4d;

import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.NetworkTablesJNI;
import edu.wpi.first.util.WPIUtilJNI;

/** Jetson NT4 client. Full scans remain on the Jetson; only diagnostic samples are sent. */
public final class CompanionMain {
  private CompanionMain() {}
  public static void main(String[] args) throws Exception {
    if (args.length != 3) throw new IllegalArgumentException("Usage: CompanionMain <bind-ip> <lidar-ip> <roborio-ip>");
    WPIUtilJNI.forceLoad();
    NetworkTablesJNI.forceLoad();
    try (var nt = NetworkTableInstance.create();
        var receiver = new L2Receiver(args[0], 6201, args[1], 6101);
        var telemetry = new L2Telemetry(nt, receiver)) {
      nt.startClient4("UnitreeL2-Jetson");
      nt.setServer(args[2]);
      while (!Thread.currentThread().isInterrupted()) {
        if (!receiver.health().running()) throw new IllegalStateException(receiver.health().error());
        telemetry.periodic();
        Thread.sleep(100); // 10 Hz compact telemetry; decoding stays on the background thread.
      }
    }
  }
}
