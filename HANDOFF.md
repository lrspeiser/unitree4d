# Continue on the 5090 machine

**Latest continuation:** [the README](README.md) now contains the Electrical Team
and Software Team instructions, including the native Windows viewer and current
bench address `192.168.0.250 -> 192.168.0.36:6201`. Some original Mac addressing
and verification notes below predate that move. Use the current README first.

Everything authored for the LiDAR setup is on this repository's `main`: source,
real captures, plots, health reports, tests, deployment examples and these
continuation notes. The FRC repositories remain separate dependencies; they have
not been modified or copied into this repository.

## User's objective

Use the Unitree 4D LiDAR L2 on Team 971's software test bot with its onboard
Jetson and existing cameras. Display a useful live point cloud alongside camera
images, gather synchronized recordings, detect/track obstacles such as another
robot, and eventually feed obstacle-aware path planning on the roboRIO.

The immediate development machine is the user's 5090 computer. Its OS and the
Jetson's installed OS/software have not been inspected. No connection to the
Jetson, roboRIO or test bot was made in this session.

## Get the checkout

```sh
git clone --branch main --recurse-submodules https://github.com/lrspeiser/unitree4d.git
cd unitree4d
```

For an existing checkout:

```sh
git switch main
git pull --ff-only
git submodule update --init --recursive
```

Read [the FRC repository map](docs/frc-repository-map.md) before choosing the
robot integration point. It contains the exact inspected commits and paths.

## Verified state

- Real L2 Ethernet input and calibrated 3D decoding work on the Apple Silicon Mac.
- Original direct-link captures used L2 `192.168.1.62:6101` and destination
  `192.168.1.2:6201`. A later home-network configuration was acknowledged:
  L2 `192.168.0.250:6101`, destination the Mac at `192.168.0.34:6201`.
  After restart, a live Wi-Fi probe decoded 641,497 points / 2,171 scans in
  10.057 seconds with no invalid packets, gaps or discontinuities; see
  [current network commissioning state](docs/home-network.md).
- The original 30-second capture decoded 1,785,215 valid points with zero packet
  framing, CRC or payload failures, about 59,500 valid points per second.
- The Java live probe decoded 479,880 points in 8.043 seconds with no invalid
  packets or observed sequence gaps.
- Java decoder parity with Unitree's C++ decoder, malformed-input rejection,
  source filtering, stale-data detection and shutdown tests pass.
- A real local NT4 client/server test verifies the diagnostic bridge and robot
  subscriber, including LiDAR silence and a frozen publisher.
- GitHub's Linux CI passed for the initial implementation commit
  `ee9627fe30642c7c4fcbe2c99f28cd982f6654d0`:
  https://github.com/lrspeiser/unitree4d/actions/runs/43107945651
- UniFi now reserves the LiDAR and Mac addresses and resolves `unitree` /
  `unitree.localdomain` to `192.168.0.250`. The LiDAR's published settings expose
  static addressing, not a documented DHCP mode. Its new static configuration
  returned a matching success ACK and survived a power cycle. The Mac's dedicated
  Ethernet adapter was restored to DHCP and disconnected; Mac Wi-Fi reception
  was verified before the destination moved to the Windows PC.

The L2 is separately powered by its supplied wall adapter. The USB adapter never
enumerated on the Mac; Ethernet solved the connection. There is no established
need for a second power supply for the UART board, and it is unnecessary on the
Ethernet path.

## Run offline verification first

On native Linux or macOS, with Make, a C++17 compiler and JDK 17+ installed:

```sh
make all test
bash scripts/build-bridge.sh
bash scripts/test-bridge.sh
```

Plot the real captures with Python, NumPy and Matplotlib:

```sh
python3 plot_scan.py results/mac-check-2026-11-11
python3 plot_near_scan.py results/hand-check-2026-11-11 1.5
python3 compare_scans.py results/hand-check-2026-11-11 results/hand-removed-2026-11-11
```

These offline checks do not need the L2, Jetson or a GPU. The supplied C++ socket
code and shell scripts target POSIX systems. On a Windows 5090, use a Linux/WSL
development environment for those tools. Live UDP reception through WSL networking
has not been verified; do not assume its virtual interface receives sensor unicast.
The pure Java receiver can also be built/run natively on Windows with JDK 17+.

For native Windows Java compilation, from PowerShell at the repository root:

```powershell
New-Item -ItemType Directory -Force build/java | Out-Null
$l2JavaSources = Get-ChildItem java/src/main/java -Recurse -Filter *.java | ForEach-Object FullName
javac --release 17 -d build/java $l2JavaSources
java -cp build/java unitree4d.L2Probe 192.168.1.2 192.168.1.62 10
```

The factory-address live command is historical and does not match the current
sensor configuration. Do not reconfigure the Windows adapter to run it. Run just
one UDP receiver at a time. Moving the sensor to the robot network requires
commissioning its source and destination addresses first.

This sensor is now commissioned on the home LAN. Its active probe command is:

```sh
java -cp build/java unitree4d.L2Probe 0.0.0.0 192.168.0.250 10
```

It previously sent to the Mac's reserved Wi-Fi IP; its destination has since been
changed to the 5090 at `192.168.0.36:6201`. Use the current README for reception
instructions. Cloning the project or resolving the sensor's hostname does not
redirect UDP data to another computer.

## The visual concern and controlled check

The user noted that the original room-wide 3D plot did not clearly resemble the
nearby person and computer. They confirmed the L2 was upright and below them.
The broad plot emphasized ceiling returns; near-field side views were clearer.

The user then explicitly confirmed a hand held roughly 50 cm from the L2, followed
by its removal. Both real captures and their occupancy comparison are stored in
`results/hand-check-2026-11-11` and `results/hand-removed-2026-11-11`. A changed
surface around that distance is consistent with the motion. It is not semantic
hand/person/computer recognition. Other differences include motion, occlusion
and sampling effects. Do not call the original image a complete optical check.

The plots are static one-second accumulations, not live video or a motion-corrected
map. Colors encode height or return intensity, not RGB. Build a live, rotatable
near-field viewer and camera/LiDAR overlay as an early next deliverable.

## Updated robot integration decision

The initial standalone Java bridge in this repository is a working bench
foundation. Subsequent source inspection found that the actual candidate Jetson
stack is Team 971's existing native C++ **COS** pipeline. The preferred production
direction is therefore to integrate the L2 as COS nodes, reusing the verified
C++ calibration/packet handling and COS's clock, camera and logging infrastructure.
Keep the roboRIO side in its existing Java robot project.

The strongest matching robot repository is **`frc971/971-prediction-bot-2026`**:
its WPILib team setting is **9972** and it consumes COS output. COS's
`vision_bot_main` also connects to **9972** and loads the four vision-bot cameras.
This is a source-code match, not proof of the software currently deployed on the
physical bot. Confirm that inventory before deployment.

The earlier deployment examples using `10.9.71.x` are generic Team 971 examples.
The matching test-team subnet would be `10.99.72.x`. Do not copy either address
plan blindly or change any robot configuration until its actual settings and
available addresses are verified.

## Next implementation sequence

1. Inspect the actual Jetson, running service, four camera serial IDs, USB topology,
   network and storage. Preserve the current working localization setup.
2. Verify camera intrinsics/extrinsics and measure the L2-to-robot transform.
   The checked COS rear camera config has zero extrinsics; do not treat it as
   validated calibration. Verify LiDAR coverage at robot-body/bumper height.
3. Add a receive-only native COS `L2SourceNode` with CRC/source checks and bounded
   buffering. Preserve raw packets, sensor time, receive time and per-point times.
4. Add synchronized raw LiDAR recording beside camera JPEGs and COS/AdvantageKit
   logs, with explicit stationary bench-recording support. Existing image logging
   is gated on Driver Station enable state, even when `--log_images` is set.
5. Display registered camera images and 3D points. Then add robot-motion compensation,
   own-robot/floor removal, voxel filtering and obstacle clustering/tracking.
6. Send compact, timestamped obstacle footprints/velocities to the roboRIO. Handle
   stale or unknown perception explicitly; missing points do not prove clear space.
7. Integrate obstacle-aware planning in replay and simulation, then controlled
   low-speed bot tests. Existing autos use BLine; setting PathPlanner obstacles
   alone will not alter those commands. See the map for integration choices.

Proposed COS node names above are new work, not existing implemented components.
No obstacle detector, full-sweep occupancy system, robot classifier, moving-robot
tracker, motion compensation or avoidance controller has been implemented here.
IMU operation, absolute range accuracy, on-Jetson runtime and robot power under
motor load remain untested. See [validation](docs/validation.md) and
[power/deployment notes](docs/frc-integration.md).

## Suggested continuation prompt

> Read HANDOFF.md and docs/frc-repository-map.md. Continue the Unitree L2 integration
> for the Team 971 software test bot, using COS on the Jetson and the matching robot
> repository. Start with synchronized recording and a live camera/point-cloud view,
> then implement and validate obstacle tracking and planner input. Preserve the
> working localization system and keep proposed functionality clearly separated
> from verified hardware behavior.
