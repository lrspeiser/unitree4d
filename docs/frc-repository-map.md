# FRC source map from the 2026-11-11 inspection

The following repositories were inspected through the user's GitHub access.
Links pin the observed commits. Some robot repositories require organization
access on the next machine. This document records integration findings; it does
not copy the robot repositories or establish what is deployed on the physical bot.

## Best matching pair

| Repository | Inspected revision | Role |
| --- | --- | --- |
| [frc971/cos](https://github.com/frc971/cos) | `f6a7bf2325c6013ae1ee627824154d5953eae9e1` | Current native Jetson camera/localization/logging stack |
| [frc971/971-prediction-bot-2026](https://github.com/frc971/971-prediction-bot-2026) | `66b821ccfd1d984c4d665e3fe493ecfd587d1abe` | Strongest matching test-bot Java code; COS pose consumer |
| [frc971/971-old-vision-bot-2026](https://github.com/frc971/971-old-vision-bot-2026) | `34bcf385aed73279f724017bd55d5b97efd6445d` | Older vision-bot implementation, using BOS |

The matching evidence is explicit: the prediction-bot
[WPILib configuration](https://github.com/frc971/971-prediction-bot-2026/blob/66b821ccfd1d984c4d665e3fe493ecfd587d1abe/.wpilib/wpilib_preferences.json)
sets team 9972, while COS's
[vision-bot entry point](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/main/vision_bot_main.cc)
calls `StartNetworktables(9972)`. The robot's
[COS.java](https://github.com/frc971/971-prediction-bot-2026/blob/66b821ccfd1d984c4d665e3fe493ecfd587d1abe/src/main/java/frc/robot/subsystems/vision/COS.java)
reads `/COS/PositionEstimate` and submits timestamped poses to the drivetrain.
Confirm the actual bot identity and deployed version before making changes.

## Camera connection and acquisition

COS's vision-bot entry point loads
[`constants/vision-bot`](https://github.com/frc971/cos/tree/f6a7bf2325c6013ae1ee627824154d5953eae9e1/constants/vision-bot):

| Direction config | Expected USB serial |
| --- | --- |
| `front.json` | `front` |
| `left.json` | `left` |
| `back.json` | `visionbotback` |
| `right.json` | `right` |

These files request UVC/MJPEG at 1280 x 800 and 100 fps. Those are requested
settings, not a measured four-camera throughput result. Camera hardware models
and the installed USB topology were not inspected. Verify actual serials and
supported modes; do not rely on enumeration order such as `/dev/video0`.

Reuse these existing components:

- [`UVCCameraConfig`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/camera/uvc_camera_config.cc): JSON configuration and serial selection.
- [`UVCCameraNode`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/camera/uvc_camera_node.cc): libuvc capture and timestamped JPEG messages.
- [`vision_bot_main`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/main/vision_bot_main.cc): camera pipelines, nvJPEG decoding, AprilTags, solver, streamer and logging.
- [`vision-bot.service`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/systemd/vision-bot.service): existing launch configuration, including `--log_images`.

The checked entry point assigns camera streams to ports 4971–4974, path `/stream`.
Inspect actual network reachability before using those URLs. It starts the camera
pipeline after NetworkTables connection/time synchronization, so a missing
roboRIO connection may prevent startup before camera acquisition begins.

The checked
[`back.json`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/constants/vision-bot/back.json)
has zero translation and rotation. Treat it as unverified mounting calibration.
The JSON convention is metres for translation and degrees for rotation; COS
converts rotations to radians internally. Measure the actual camera and LiDAR
mounts before registering points or fusing detections.

## Recording and synchronization

- [`RioClock`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/control_loop/rio_clock.cc) translates the Jetson clock using the NetworkTables server-time offset.
- [`JpegBufferLogNode`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/logging/jpeg_buffer_log_node.cc) writes per-camera JPEGs with timestamps in filenames.
- [`ShouldLogImages`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/control_loop/connect_to_rio.cc) gates images using Driver Station enable state and connection status.
- [`WPILogWriter`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/logging/wpilog_writer.cc) records COS publications. Default run folders are under `/cos/logs/logN`.
- [`jpeg_disk_replay`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/tools/jpeg_disk_replay.cc) and the repository's tests provide offline camera replay infrastructure.

Proposed additions: chunked raw L2 packet logs with host and sensor timestamps,
sequence IDs and loss counts; sensor-to-robot/camera calibration snapshots; robot
pose/velocity history; registered point clouds; and obstacle tracks. Reuse the
same run ID and common clock. Keep sensor time separate until its offset and
timing behavior are verified. Preserve each point's relative measurement time
for motion compensation; the current PLY snapshots do not retain all of this.

Add an explicit bench-recording mode rather than relying on robot enable just to
record stationary camera data. Do not silently change the existing enabled-state
recording policy for normal robot operation.

## Point cloud and obstacle processing

Reuse Unitree's calibrated C++ conversion through this repository's pinned SDK
and the proven payload CRC handling in `l2_mac_check.cpp`. Extract that logic into
a bounded receive-only source compatible with COS's node/message system.

The proposed processing chain is:

```text
L2 packets -> calibrated points + times -> sensor-to-robot transform
           -> robot-motion compensation -> floor / self-robot filtering
           -> voxel reduction -> clusters / occupancy -> obstacle tracks
           -> field-frame footprints + timestamps -> roboRIO
```

Useful external building blocks:

- [PCL VoxelGrid](https://pointclouds.org/documentation/tutorials/voxel_grid.html) for downsampling.
- [PCL PassThrough](https://pointclouds.org/documentation/tutorials/passthrough.html) for explicit spatial filters.
- [PCL EuclideanClusterExtraction](https://pointclouds.org/documentation/tutorials/cluster_extraction.html) for grouping returns.

The pipeline itself is not implemented in the checked COS or robot branch.
Use measured robot geometry and uncertainty to expand occupied footprints.
Handle occlusion and stale/unobserved regions explicitly. Upright L2 coverage is
mostly above its base: verify that the mount sees nearby robot bodies rather
than only structures above them.

COS already contains a TensorRT
[`YoloNode`](https://github.com/frc971/cos/blob/f6a7bf2325c6013ae1ee627824154d5953eae9e1/src/gamepiece/yolo_node.h)
with configurable model/classes. It can supply an inference framework for later
robot classification, but no verified robot-detection model was established in
this inspection. Avoidance can begin with geometric obstacles; camera labels
should not determine whether an occupied region is ignored.

## Robot-side path planning

The inspected robot's
[`Autos.java`](https://github.com/frc971/971-prediction-bot-2026/blob/66b821ccfd1d984c4d665e3fe493ecfd587d1abe/src/main/java/frc/robot/subsystems/drive/Autos.java)
uses BLine `FollowPath.Builder`. A PathPlanner 2026.1.2 vendor dependency is also
present, but no current LiDAR/dynamic-obstacle feed was found.

PathPlanner's
[`Pathfinding.setDynamicObstacles`](https://pathplanner.dev/api/java/com/pathplanner/lib/pathfinding/Pathfinding.html)
accepts field-space rectangles and the robot position. This is a candidate
integration point for new obstacle-aware commands, not an automatic extension
to the current BLine commands. Explicitly choose and test either new pathfinding
commands or a planner/follower bridge. Keep stale-data handling and a conservative
stop/hold policy independent of successful global replanning.

Use the existing robot logging and MapleSim support to test replay and simulated
crossing robots before commanding motion. See
[PathPlanner's pathfinding guide](https://pathplanner.dev/pplib-pathfinding.html),
including its AdvantageKit-compatible pathfinder guidance for deterministic replay.

The first deliverable should be synchronized data collection and a useful live
camera/point-cloud/obstacle display. Closed-loop robot avoidance remains later
work and was not enabled during this session.
