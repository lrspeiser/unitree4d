# Verification on 2026-11-11

Tests were run on the connected Apple Silicon Mac, with the real L2 at
`192.168.1.62`, receiver at `192.168.1.2:6201`. No sensor configuration or home
router settings were changed. Only the Mac's dedicated Ethernet adapter was
configured to the sensor's factory subnet.

| Check | Observed result |
| --- | --- |
| Original native capture | 6,477 valid 3D packets in 30.0036 s |
| Valid points in original capture | 1,785,215, about 59,500/s |
| Original frame / CRC / payload failures | 0 / 0 / 0 |
| Follow-up native capture | 1,728 scans, 477,171 points in 8.00405 s |
| Follow-up sequence gaps / unexpected resets | 0 / 0; two normal 1024-counter wraps |
| Java live probe | 1,735 scans, 479,880 points in 8.043 s |
| Java invalid packets / observed gaps | 0 / 0 |
| Java vs official C++ conversion | 260 points in real fixture; max XYZ difference 0.0000567 m |
| Corrupt packet tests | Bad header, CRC, truncation, out-of-bounds count, NaN calibration and invalid time rejected |
| UDP receiver tests | Source-port filtering, silence, corrupted-packet staleness and close/shutdown pass |
| Local real NT4 client/server test | UDP data reaches robot subscriber; sensor silence and frozen-publisher cache rejected |

The 30-second run's original sequence counter report classified six decreases
as `sequence_resets_or_reorder`. A focused follow-up observed the actual normal
transition `1023 -> 0`. The receiver now counts normal wraps separately. The
original report remains available with that context; do not interpret its six
decreases as six confirmed sensor resets.

The dirty indicator varied through 0–31.7%, averaging about 8.1% in the original
run. No undocumented optical-condition pass/fail threshold is applied. The APD
temperature reported roughly 42–44 C in these captures; it is a sensor telemetry
field, not a measurement of the external case temperature.

## Visual check

The original view showed the complete last one second of returns, making the
room ceiling visually prominent. Later near-field side plots isolate nearby
surfaces without changing the saved raw point clouds. The user confirmed the
sensor was upright and below the person/monitor.

For a controlled check, the user held a hand roughly 50 cm from the sensor,
then explicitly confirmed its removal. Both captures are stored. A 4 cm voxel
occupancy comparison showed a changed near-field surface consistent with that
motion, including a cluster centred approximately 0.51 m from the sensor.
Other surfaces changed too; motion, occlusion and sampling are confounders.
This does not establish semantic recognition of a hand, person or computer.

## Limits

No Jetson, roboRIO or robot power system was connected for this verification.
There is no on-robot runtime/CPU/latency evidence yet. IMU operation, absolute
ranging accuracy, mounting extrinsics, motion compensation and autonomous
obstacle behavior remain untested. A latest-slice diagnostic is not a full-sweep
perception algorithm. See the integration guide for the remaining work.
