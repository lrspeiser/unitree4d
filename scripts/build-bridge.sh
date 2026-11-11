#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
version=2026.2.2
platform="${L2_PLATFORM:-}"
if [[ -z "$platform" ]]; then
  case "$(uname -s)/$(uname -m)" in
    Linux/aarch64|Linux/arm64) platform=linuxarm64 ;;
    Linux/x86_64) platform=linuxx86-64 ;;
    Darwin/*) platform=osxuniversal ;;
    *) echo 'Set L2_PLATFORM to a WPILib native classifier for this platform.' >&2; exit 1 ;;
  esac
fi
mkdir -p build/bridge/lib build/bridge/native build/bridge/downloads build/java
for module in wpiutil wpinet ntcore; do
  for suffix in java cpp; do
    artifact="$module-$suffix"
    classifier=""
    extension=jar
    directory=lib
    if [[ "$suffix" == cpp ]]; then
      classifier="-$platform"; extension=zip; directory=downloads
    fi
    destination="build/bridge/$directory/$artifact-$version$classifier.$extension"
    if [[ ! -f "$destination" ]]; then
      curl -fLsS --retry 2 "https://frcmaven.wpi.edu/artifactory/api/download/release/edu/wpi/first/$module/$artifact/$version/$artifact-$version$classifier.$extension" -o "$destination.part"
      jar tf "$destination.part" >/dev/null
      mv "$destination.part" "$destination"
    fi
    if [[ "$suffix" == cpp ]]; then
      unzip -jo "$destination" '*/shared/*' -d build/bridge/native >/dev/null
      mkdir -p "build/bridge/licenses/$module"
      unzip -p "$destination" LICENSE.md > "build/bridge/licenses/$module/LICENSE.md"
      unzip -p "$destination" ThirdPartyNotices.txt > "build/bridge/licenses/$module/ThirdPartyNotices.txt"
    fi
  done
done
make java
javac --release 17 -Xlint:all -cp 'build/java:build/bridge/lib/*' -d build/java examples/wpilib/unitree4d/*.java
jar --create --file build/bridge/unitree4d.jar -C build/java unitree4d
echo "Built NetworkTables bridge for $platform with WPILib $version"
