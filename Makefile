CXX ?= c++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra
SDK_INCLUDE = unilidar_sdk2/unitree_lidar_sdk/include
JAVA_SOURCES = $(shell find java/src/main/java -name '*.java')
TEST_SOURCES = $(shell find java/src/test/java -name '*.java')

.PHONY: all java test clean
all: build/l2_mac_check java

build/l2_mac_check: l2_mac_check.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -I $(SDK_INCLUDE) $< -o $@

java:
	mkdir -p build/java
	javac --release 17 -Xlint:all -d build/java $(JAVA_SOURCES)

build/reference: tests/reference_decode.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -I $(SDK_INCLUDE) $< -o $@

test: java build/reference
	build/reference tests/fixtures/l2-scan.bin > build/reference.csv
	javac --release 17 -Xlint:all -cp build/java -d build/java $(TEST_SOURCES)
	java -cp build/java unitree4d.L2Tests

clean:
	rm -rf build
