#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
javac --release 17 -Xlint:all -cp 'build/java:build/bridge/lib/*' -d build/java tests/BridgeTests.java
export LD_LIBRARY_PATH="$PWD/build/bridge/native${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
java -Djava.library.path="$PWD/build/bridge/native" \
  -cp 'build/java:build/bridge/lib/*' unitree4d.BridgeTests
