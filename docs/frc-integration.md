# FRC diagnostic bridge reference

For current student setup and purchasing, start with [the README](../README.md)
and [electrical build guide](electrical-team-build-guide.md). The Java bridge below
is diagnostic-only and has not been deployed to the bot. Address tables are
examples, not the current sensor or verified bot network.

Updated source inspection: see [the FRC repository map](frc-repository-map.md).
The strongest matching test-bot/COS pair uses team **9972**, and its existing
Jetson pipeline is native C++. The Java bridge below remains a tested standalone
foundation; native COS integration is the preferred next production step.
The Team 971 addresses below are illustrative, not confirmed test-bot settings.

## Recommended arrangement

Use the onboard Jetson to receive the full scan stream. Keep robot actuation
and the normal robot loop on the roboRIO. The Java receiver can also be copied
directly into a roboRIO Java project for diagnostics, but full-scan processing
has not been profiled on that controller. No GPU is required for basic decoding.
The Jetson's extra compute is useful for later filtering, registration and mapping.

The implementation is compatible with Java 17 and uses no proprietary native
LiDAR library. The standalone NT bridge pins WPILib **2026.2.2** and downloads
the appropriate native libraries. Existing robot projects should use their own
WPILib dependencies and copy the example source, without mixing JNI versions.

## Power and mounting

The L2 needs **12 V DC** on the power lead in its three-way cable. Unitree lists
12 V / 1 A in troubleshooting and describes startup/self-heating power reaching
13 W. For the test bot, use a protected distribution branch feeding a regulated
12 V converter with startup headroom; a 2 A continuous output is a design target,
not a verified rating of any module presently installed on this bot. Select an
input range that covers the actual battery voltage and expected sag under load.
The exact regulator, wiring gauge and branch protection remain to be selected.

Check the actual connector, polarity and output voltage before connecting the
sensor. The manual identifies the power connector as approximately 3.5 x 1.35 mm;
verify the supplied hardware before buying or making a cable. Ethernet is the
data connection; power still uses the separate lead. The UART board is not needed.
Power the Jetson according to its own model's requirements, on a suitably sized
supply. It does not power the L2 over Ethernet.

Mount the L2 securely with the optical field clear of robot structure. The
initial Mac plots use the L2 frame: +X opposite the cable outlet, +Y to its left,
+Z above its base. A robot installation needs a measured sensor-to-robot transform.
Point ranges and headings are not robot coordinates until that transform is applied.

If the regulator input is wired to an appropriate REV PDH switchable output,
software can switch that branch using the bot's existing `PowerDistribution`
object:

```java
// Only after confirming that this physical branch powers the L2 regulator.
pdh.setSwitchableChannel(true);   // supply the regulator input
pdh.setSwitchableChannel(false);  // remove power
```

That output switches its supply; it does not regulate it to 12 V. This method
is specific to a REV PDH, not a CTRE PDP. Do not cycle power every robot enable:
the L2 needs time to spin up and warm up. Receiver freshness gates data use after
startup and after any loss of power. This repository does not modify the robot's
power distribution or issue power commands automatically.

## Onboard Ethernet

Use an onboard switch so the L2, Jetson and roboRIO share the wired robot network.
Keep the high-rate cloud on that network and on the Jetson. The bridge publishes
seven diagnostic numbers at 10 Hz; it does not broadcast raw clouds to the driver
station or command the drivetrain.

Example addresses for **Team 971**, subject to the actual bot's address plan:

| Device | Address | Role |
| --- | --- | --- |
| roboRIO | `10.9.71.2` | Existing NT server |
| Jetson | `10.9.71.11` | UDP receiver and NT client |
| L2 | `10.9.71.12` | UDP source port 6101 |
| L2 destination | `10.9.71.11:6201` | Jetson receiver |

Use subnet mask `255.255.255.0`. Confirm addresses are unused before applying
them. These addresses are examples, not settings applied to the current L2.
The last verified bench settings are `192.168.0.250:6101 -> 192.168.0.36:6201`.
The original direct-link Mac addresses are historical.

Commission the L2's new network settings while a computer can still reach the
old address, using Unitree's configuration software or its
`unitree_lidar_sdk/examples/set_ip_address.cpp`. Set the LiDAR IP, destination IP,
subnet and both UDP ports to the values above; follow Unitree's save/restart
procedure and verify receipt on the new subnet. The example's hard-coded initial
and target addresses must be edited to the actual current settings before use.
The repository now includes `l2_network.py` for read-only queries and staged
configuration. Writes require explicit `--apply` and confirmed addresses; simply
moving the Ethernet cable to the robot network will not finish commissioning.

For a direct roboRIO receiver instead, change the L2 destination to the roboRIO's
address and run the same receiver inside robot code. The L2 sends to one configured
destination. A different listening computer will not automatically receive that
unicast stream.

## Build and run on the Jetson

Install JDK 17+, a C++17 compiler, Make, Git, curl and unzip through the Jetson's
normal Ubuntu package manager. The Jetson model, JetPack version, available RAM
and native-library compatibility have not yet been inspected.

```sh
git clone --recurse-submodules https://github.com/lrspeiser/unitree4d.git
cd unitree4d
make all test
bash scripts/build-bridge.sh
bash scripts/test-bridge.sh
```

The build script selects `linuxarm64` automatically on an ARM64 Jetson. Build
there rather than copying the Mac's native dependency files. First run only the
read-only probe with the actual configured addresses:

```sh
java -cp build/java unitree4d.L2Probe 0.0.0.0 10.9.71.12 10
```

Then run the NT bridge:

```sh
bash scripts/run-bridge.sh 0.0.0.0 10.9.71.12 10.9.71.2
```

Binding to `0.0.0.0` allows the service to start before a particular interface
is ready. It is not the destination address configured in the L2; that must be
the Jetson's actual address. The receiver accepts only the configured source IP
and source port 6101. A missing sensor is reported as stale, while socket failure
ends the bridge so the service manager can restart it.

For supervised startup, place the checkout at `/opt/unitree4d`, create the
unprivileged service user `unitree`, grant it read access to that checkout and
its built dependencies, and give it a writable home directory. Copy and edit
`deploy/unitree-l2.env.example` to `/etc/unitree-l2.env`, then install the supplied
service:

```sh
sudo cp deploy/unitree-l2.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now unitree-l2
journalctl -u unitree-l2 -f
```

These installation commands have not been executed on the bot. The application
uses UDP port 6201 and outgoing NT4 to the roboRIO; allow those on the Jetson's
local firewall if one is enabled. No root privileges are required to receive data.

## Robot-side integration

Copy `examples/wpilib/unitree4d/L2RobotInput.java` into the Java robot project
under `src/main/java/unitree4d/`. Use the project's existing WPILib dependencies.

```java
private final L2RobotInput lidar =
    new L2RobotInput(NetworkTableInstance.getDefault());

// Called from robotPeriodic(), with no blocking socket reads:
var latest = lidar.latestFresh();
if (latest.isPresent()) {
    double[] sample = latest.get();
    // sample[2] is the current slice's point count.
    // sample[3] is the nearest return in that single slice, in metres.
    // Add logging/dashboard display here; no actuation is wired to this example.
} else {
    // Treat perception as unavailable; never reuse an old obstacle/clearance result.
}
```

Close the subscriber during program teardown. For direct roboRIO reception,
also copy the three core classes under `java/src/main/java/unitree4d/`, construct
one `L2Receiver`, and query `latestFresh(Duration.ofMillis(250))` in periodic code.
Do not construct receivers repeatedly inside periodic methods.

The `/UnitreeL2/sample` double array is one atomic diagnostic record:

| Index | Meaning |
| --- | --- |
| 0 | Fresh flag: 1 or 0 |
| 1 | Sensor scan-slice sequence |
| 2 | Valid point count in that slice |
| 3 | Nearest return in that slice, metres; NaN when unavailable |
| 4 | Sensor dirty index |
| 5 | APD temperature, Celsius |
| 6 | Local receive age at publication, seconds |

NetworkTables supplies the publication timestamp and clock synchronization. The
robot subscriber combines transport/publication age with field 6 and rejects a
sample older than 300 ms. The bridge sends explicit unavailable samples after
250 ms without a valid scan. Independently aging the NT value catches a crashed
or frozen bridge that left a cached `fresh=1` value behind.

One packet spans about 4.6 ms, not a full 360-degree sweep. Its nearest return
is not an all-around clearance or collision-avoidance result. The sensor clock
is unsynchronized; receive timestamps are not exposure timestamps suitable for
pose fusion. Full-sweep aggregation, mounting transform, time synchronization,
motion compensation and actual obstacle logic must be implemented and tested
before using perception to command motion.

## Remaining on-bot work

Select and bench-test the power converter; commission the actual network;
install the bridge on the Jetson; profile CPU, latency and dropped packets; and
verify power-up, motor-load voltage sag, network unplug/reconnect and stale-data
behavior with the real robot. The local tests do not establish these results.

Sources: [Unitree L2 manual](https://oss-global-cdn.unitree.com/static/Unitree%204D%20LiDAR%20L2%20User%20Manual.pdf),
[Unitree SDK](https://github.com/unitreerobotics/unilidar_sdk2),
[WPILib addressing](https://docs.wpilib.org/en/2025/docs/networking/networking-introduction/ip-configurations.html),
[WPILib NT client programs](https://docs.wpilib.org/en/stable/docs/software/networktables/client-side-program.html),
[NetworkTables timestamps](https://docs.wpilib.org/en/stable/docs/software/networktables/networktables-intro.html),
[WPILib PowerDistribution API](https://github.wpilib.org/allwpilib/docs/release/java/edu/wpi/first/wpilibj/PowerDistribution.html).
