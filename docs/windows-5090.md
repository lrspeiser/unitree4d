# 5090 continuation (2026-11-11)

Local checkouts: ../unitree4d, ../cos, ../971-prediction-bot-2026.
Ubuntu-24.04 WSL is installed. Java is not available on the Windows PATH.

Verified sensor: unitree.localdomain / 192.168.0.250, MAC 0C-29-AB-7C-00-01,
YS-L2, hardware 2.2.1.1, firmware 2.8.11.1. Native Windows read-only identity query works.

Previous stream destination: Mac 192.168.0.34:6201.
Current destination: Windows 192.168.0.36:6201; source 192.168.0.250:6101,
gateway 192.168.0.1 and mask 255.255.255.0 unchanged. Applied with type-108 success ACK; live reception verified on Windows.
Do not change Windows adapter addresses, DHCP, gateway or DNS.
Reserve the PC's current lease in UniFi before relying on it long term.

## Native Windows viewer
Use [the repository's Python viewer](../README.md#1-get-this-repository-and-run-an-offline-viewer-first).
It has been verified with real UDP input on Windows at 192.168.0.36:6201, accepting
sensor 192.168.0.250:6101. It serves its UI only at http://127.0.0.1:8765.
The Windows Unilidar V1.21 executable was blocked by Defender as
Trojan:Win32/Ravartar!rfn; do not run it or bypass that detection.
Run only one receiver at a time. No Windows adapter, DHCP, DNS, route, or firewall
changes are part of this workflow. See [viewer and recording notes](viewer-and-cos.md).

## COS integration
Current COS checkout matches inspected f6a7bf2. Preserve existing localization.
Use native Windows for first live reception; WSL sensor unicast is not verified.
Use WSL for POSIX decoder parity/build tests, then develop a receive-only L2 source
with bounded storage, validated framing/CRC, source filtering and per-point timing.
First integration output: raw synchronized LiDAR recording and camera/point-cloud display.
Use COS RioClock and logging infrastructure; add explicit stationary bench recording
because camera logs are gated on DS enabled state. Verify physical bot, camera calibration
and L2 transform before deployment. Team-9972 prediction bot is the source-code match.
Obstacle tracking, motion compensation and planner control remain future work.
See frc-repository-map.md for exact integration points and limitations.

## Sensor change already applied with user approval
The L2 accepted the destination change to this PC with a type-108 status-1 ACK,
and live scan reception was subsequently verified. This is a completed change,
not a command to repeat. The source remains 192.168.0.250:6101.
For a future robot-network move, stage and review the actual addresses using
[the commissioning worksheet](electrical-team-build-guide.md#commission-the-robot-network).
Only explicitly approved sensor writes should be applied; preserve the PC networking.
