# Real L2 packet fixture

`l2-scan.bin` is one actual 1044-byte type-102 UDP packet captured on 2026-11-11
from the connected L2 at `192.168.1.62:6101`. Its calibration fields and ranges
are genuine. The payload CRC is checked before decoding.

`make test` decodes this fixture through Unitree's pinned C++ header and the new
Java decoder, comparing every accepted point. No simulated scene replaces the
real packet. Mutated copies are used only for malformed-input tests.

SHA-256: `09cebfea9d69e292fad777d0071178a6ed42275e448b9f4e0c3fe8e0ac7cb42a`.
