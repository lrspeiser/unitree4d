# Third-party source and runtime dependencies

Unitree Robotics' `unilidar_sdk2` is a Git submodule pinned to
`0e3c51f512e6b8ff60b8c32f160b412cb48445c2`:
https://github.com/unitreerobotics/unilidar_sdk2

Its BSD 3-Clause license and copyright notices remain in the submodule.
`L2PacketDecoder.java` and `point_viewer.py` adapt the calibration math from
`unitree_lidar_sdk/include/unitree_lidar_utilities.h`; its Unitree copyright
notice is retained and the root BSD 3-Clause license includes that attribution.

The optional NetworkTables bridge downloads WPILib 2026.2.2 Java and native
runtime dependencies from FIRST/WPI's official Maven repository. Downloaded
artifacts are build outputs, not committed source. The build also extracts
their license and third-party notices into `build/bridge/licenses/`; retain
those files when distributing the built bridge.

The Python viewer/exporter use the separately installed NumPy dependency in
`requirements-viewer.txt`. The plotting helpers also use Matplotlib.
They are not bundled in this repository. The real scan captures and verification
results were generated during this setup session.
