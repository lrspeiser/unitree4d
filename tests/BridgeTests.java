package unitree4d;

import edu.wpi.first.networktables.NetworkTableInstance;
import edu.wpi.first.networktables.NetworkTablesJNI;
import edu.wpi.first.util.WPIUtilJNI;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.file.Files;
import java.nio.file.Path;

/** Actual UDP -> decoder -> NT4 client -> NT4 server -> roboRIO subscriber logic. */
public final class BridgeTests {
  private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
  public static void main(String[] args) throws Exception {
    WPIUtilJNI.forceLoad(); NetworkTablesJNI.forceLoad();
    int tcpPort, udpPort;
    try (var reservation = new ServerSocket(0)) { tcpPort = reservation.getLocalPort(); }
    try (var reservation = new DatagramSocket(0)) { udpPort = reservation.getLocalPort(); }
    byte[] packet = Files.readAllBytes(Path.of("tests/fixtures/l2-scan.bin"));
    try (var sender = new DatagramSocket(0);
        var receiver = new L2Receiver("127.0.0.1", udpPort, "127.0.0.1", sender.getLocalPort());
        var server = NetworkTableInstance.create(); var client = NetworkTableInstance.create();
        var publisher = new L2Telemetry(client, receiver); var input = new L2RobotInput(server)) {
      server.startServer("", "127.0.0.1", 0, tcpPort);
      client.startClient4("L2-integration-test"); client.setServer("127.0.0.1", tcpPort);
      long deadline = System.nanoTime() + 5_000_000_000L;
      while (input.latestFresh().isEmpty() && System.nanoTime() < deadline) {
        sender.send(new DatagramPacket(packet, packet.length, InetAddress.getLoopbackAddress(), udpPort));
        Thread.sleep(20); publisher.periodic(); client.flush(); Thread.sleep(30);
      }
      check(input.latestFresh().isPresent(), "No fresh scan crossed actual NT4 connection");
      check(input.latestFresh().orElseThrow()[2] > 0, "Point count was not transmitted");
      // Publisher stays alive, but LiDAR stops: publish explicit stale status.
      Thread.sleep(300); publisher.periodic(); client.flush(); Thread.sleep(100);
      check(input.latestFresh().isEmpty(), "LiDAR silence accepted by robot subscriber");
      // Reconnect sensor, then freeze publisher entirely: subscriber must age out cached fresh=true.
      sender.send(new DatagramPacket(packet, packet.length, InetAddress.getLoopbackAddress(), udpPort));
      Thread.sleep(30); publisher.periodic(); client.flush(); Thread.sleep(80);
      check(input.latestFresh().isPresent(), "Did not recover after new sensor data");
      Thread.sleep(350);
      check(input.latestFresh().isEmpty(), "Frozen bridge's cached sample remained fresh");
    }
    System.out.println("PASS: UDP -> real NT4 client/server -> robot subscriber; LiDAR silence and frozen bridge rejected");
  }
}
