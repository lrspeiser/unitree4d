# Original Unitree L2 Mac verification

**Historical direct-link setup.** The sensor was later readdressed to
`192.168.0.250`, sending to the 5090 at `192.168.0.36:6201`. Use
[the current team instructions](../README.md) for new work. Do not change the
5090 network settings or assume the old addresses below are still active.

The direct Ethernet connection was verified on 2026-11-11. The Mac receives
3D scan packets from `192.168.1.62:6101` at `192.168.1.2:6201`.
The L2 remains in its existing Ethernet mode; no sensor settings were changed.

The Mac network service **USB 10/100/1G/2.5G LAN** (`en10`) was changed from DHCP
to manual IPv4 `192.168.1.2`, subnet `255.255.255.0`, with no router.
Wi-Fi remains the internet connection. When reusing this Ethernet adapter for
the home network, restore its IPv4 setting to DHCP in System Settings, or run:

```sh
networksetup -setdhcp 'USB 10/100/1G/2.5G LAN'
```

## Run another check

Keep the L2 powered by its supplied adapter, with its Ethernet cable connected
directly to the Mac's Ethernet adapter. Only one receiver can use UDP port 6201
at a time.

From the repository root:

```sh
clang++ -O2 -std=c++17 -Wall -Wextra \
  -I unilidar_sdk2/unitree_lidar_sdk/include l2_mac_check.cpp -o l2_mac_check
./l2_mac_check 30 results/latest
python3 plot_scan.py results/latest
```

`l2_mac_check` is a receive-only native macOS program. It checks packet framing,
payload CRCs, packet lengths, scan sequence continuity and finite 3D coordinates.
It uses Unitree's actual inline calibrated conversion function, without linking
the Linux-only SDK binary. The checksum of the observed L2 datagrams covers the
payload, excluding header and tail. The observed scan sequence wraps at 1024.

Outputs are `health.json`, `scan.ply` and, after plotting, `scan-preview.png`.
The PLY contains the latest approximately one second of points in metres. This
accumulation assumes the sensor stays still; it is not a motion-corrected map.
The plot requires NumPy and Matplotlib, already available on this Mac.

The first 30-second run is saved in `results/mac-check-2026-11-11`. Its original
sequence diagnostic grouped six counter decreases under
`sequence_resets_or_reorder`. A follow-up measurement confirmed the normal
counter transition is `1023 -> 0`; the utility now counts that separately.

Checks establish basic Ethernet communication and calibrated point decoding.
They do not establish absolute ranging accuracy or validate the IMU. The
sensor's `dirty_index` is recorded as telemetry; no undocumented pass/fail
threshold is applied.

The official SDK checkout is `unilidar_sdk2`, revision
`0e3c51f512e6b8ff60b8c32f160b412cb48445c2`:
https://github.com/unitreerobotics/unilidar_sdk2
