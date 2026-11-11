#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root="$PWD"
export LD_LIBRARY_PATH="$root/build/bridge/native${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec java -Xms32m -Xmx256m -Djava.library.path="$root/build/bridge/native" \
  -cp "$root/build/bridge/unitree4d.jar:$root/build/bridge/lib/*" \
  unitree4d.CompanionMain "$@"
