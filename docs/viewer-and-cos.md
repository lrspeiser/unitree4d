# 5090 viewer and COS recording contract

Run from this repository: `python point_viewer.py`, then open http://127.0.0.1:8765.
Requires Python and NumPy (already installed on this machine). HTTP listens only on
loopback. UDP binds the existing 192.168.0.36:6201, accepts only 192.168.0.250:6101.
No commands are sent, and no adapter, DHCP, DNS, route or firewall changes are made.
Drag to rotate, wheel to zoom, filter by range, or choose top/side view.
Points accumulate for 0.6 seconds. Stale points disappear and the status reports silence.
This is a stationary accumulation, without motion correction or camera registration.

For a bounded capture: `python point_viewer.py --record tmp/session.jsonl --record-seconds 60`.
Existing capture files are never overwritten. One receiver at a time.
For a fixture demonstration: `python point_viewer.py --replay tests/fixtures/l2-scan.bin`.
Replay repeats one slice; it is not a live full scene.

Decoder tests compare 260 fixture points against Unitree's C++ reference, within
0.1 mm coordinate tolerance and exact intensity equality, and reject corrupted CRCs
and truncated frames. C++ uses float arithmetic; this Python implementation uses double.
The UI caps output at 25,000 points; full validated slices remain in the raw recording.

## Implemented recording interchange
Each JSONL row preserves the full wire packet, sensor seconds/nanoseconds, sequence,
reported point step, Windows receive monotonic nanoseconds and Unix nanoseconds.
`python export_recording.py tmp/session.jsonl tmp/session.npz` exports calibrated xyzi,
slice offsets and metadata for replay/obstacle algorithm work. JSON hex is a bench
format with considerable overhead, not a final on-robot log format.
Windows monotonic timestamps are local to this host and must not be equated with RioClock.
Point-step semantics, sensor/host offset and motion compensation remain unverified.

## COS integration decisions from inspected source
COS INode declares publications/dependencies, registers callbacks and sets messages
on each triggered Context. UVCCameraNode is an asynchronous source to follow.
A production L2SourceNode should receive on a dedicated socket thread, validate the
same frames/CRC/calibration, and publish an immutable bounded scan message to COS.
The message must own xyzi, raw bytes, sensor time, host steady receive time, sequence,
per-point timing, source endpoint and health. Do not publish raw pointers into a
reused receive buffer. Publish null on stale data; never silently reuse old scans.
Use RioClock only after its synchronization is established; retain original clocks.

Next gate: replay these captures through a native C++ source independent of hardware,
then adapt to COS and test shutdown, loss, corruption, source filtering and stale data.
Reuse JpegBufferLogNode/WPILogWriter and a common run ID. Explicit stationary bench
logging is required because existing image logging depends on DS enable state.
The source-code match is frc971/971-prediction-bot-2026, team 9972. Verify the physical
bot before deployment. Preserve existing localization and autos. No robot software
was deployed, and no obstacle-avoidance or camera-registration claims are made.
