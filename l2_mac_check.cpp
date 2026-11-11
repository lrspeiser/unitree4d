#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <chrono>
#include <csignal>
#include <cstring>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <vector>
#include "unitree_lidar_utilities.h"

using namespace unilidar_sdk2;
using Clock = std::chrono::steady_clock;
static volatile sig_atomic_t running = 1;
static void stop(int) { running = 0; }

// Receive only: this utility never sends commands or changes the sensor.
int main(int argc, char** argv) {
    try {
        const double duration = argc > 1 ? std::stod(argv[1]) : 20;
        if (!std::isfinite(duration) || duration <= 0) throw std::runtime_error("Duration must be positive");
        const std::filesystem::path out = argc > 2 ? argv[2] : "results";
        std::filesystem::create_directories(out);
        static_assert(sizeof(LidarPointDataPacket) == 1044);
        static_assert(sizeof(FrameTail) == 12);
        int fd = socket(AF_INET, SOCK_DGRAM, 0);
        if (fd < 0) throw std::runtime_error("Cannot create UDP socket");
        timeval timeout{1, 0};
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        int receiveSize = 2 * 1024 * 1024;
        setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &receiveSize, sizeof(receiveSize));
        sockaddr_in local{};
        local.sin_family = AF_INET;
        local.sin_port = htons(6201);
        inet_pton(AF_INET, "192.168.1.2", &local.sin_addr);
        if (bind(fd, reinterpret_cast<sockaddr*>(&local), sizeof(local)) < 0) {
            close(fd);
            throw std::runtime_error("Cannot bind 192.168.1.2:6201; check Ethernet address and other receivers");
        }
        std::signal(SIGINT, stop);
        const auto start = Clock::now();
        auto lastPrint = start;
        uint64_t packets = 0, badFrame = 0, badCRC = 0, badPayload = 0, nonfinite = 0;
        uint64_t scans = 0, points = 0, rawPoints = 0, seqGaps = 0, seqResets = 0, duplicates = 0;
        uint64_t seqWraps = 0;
        std::map<uint32_t, uint64_t> types;
        uint32_t lastSeq = 0;
        bool haveSeq = false;
        double dirtySum = 0, dirtyMin = 1e10, dirtyMax = -1e10;
        double tempMin = 1e10, tempMax = -1e10;
        double lostUpMax = 0, lostDownMax = 0;
        double firstData = -1, lastData = -1;
        LidarInsideState state{};
        struct Batch { double time; std::vector<PointUnitree> points; };
        std::deque<Batch> window;
        std::vector<uint8_t> buffer(65536);
        PointCloudUnitree cloud;
        std::cout << "Listening to L2 at 192.168.1.62 -> 192.168.1.2:6201 for " << duration << " s\n" << std::flush;
        while (running && std::chrono::duration<double>(Clock::now() - start).count() < duration) {
            sockaddr_in from{};
            socklen_t fromLen = sizeof(from);
            auto n = recvfrom(fd, buffer.data(), buffer.size(), 0, reinterpret_cast<sockaddr*>(&from), &fromLen);
            if (n < 0) continue;
            if (from.sin_addr.s_addr != inet_addr("192.168.1.62") || ntohs(from.sin_port) != 6101) continue;
            ++packets;
            double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
            if (firstData < 0) firstData = elapsed;
            lastData = elapsed;
            FrameHeader head{};
            if (n < static_cast<ssize_t>(sizeof(FrameHeader) + sizeof(FrameTail))) { ++badFrame; continue; }
            std::memcpy(&head, buffer.data(), sizeof(head));
            FrameTail tail{};
            std::memcpy(&tail, buffer.data() + n - sizeof(tail), sizeof(tail));
            if (std::memcmp(head.header, "\x55\xaa\x05\x0a", 4) || head.packet_size != n || tail.tail[0] != 0 || tail.tail[1] != 255) {
                ++badFrame; continue;
            }
            // L2 wire packets checksum the payload, excluding header and tail.
            if (crc32(buffer.data() + sizeof(head), n - sizeof(head) - sizeof(tail)) != tail.crc32) { ++badCRC; continue; }
            ++types[head.packet_type];
            if (head.packet_type != LIDAR_POINT_DATA_PACKET_TYPE) continue;
            if (n != sizeof(LidarPointDataPacket)) { ++badPayload; continue; }
            LidarPointDataPacket packet{};
            std::memcpy(&packet, buffer.data(), sizeof(packet));
            if (packet.data.point_num > 300 || packet.data.info.payload_size != sizeof(LidarPointData) || packet.data.info.stamp.nsec >= 1000000000) {
                ++badPayload; continue;
            }
            const uint32_t seq = packet.data.info.seq;
            if (haveSeq) {
                const uint32_t delta = seq - lastSeq;
                // This L2's counter was observed wrapping 1023 -> 0.
                if (lastSeq == 1023 && seq == 0) ++seqWraps;
                else if (delta == 0) ++duplicates;
                else if (delta > 1 && delta < 10000) seqGaps += delta - 1;
                else if (delta >= 10000) ++seqResets;
            }
            lastSeq = seq; haveSeq = true;
            parseFromPacketToPointCloud(cloud, packet, false, 0.05f, 40.0f);
            std::vector<PointUnitree> finite;
            finite.reserve(cloud.points.size());
            for (const auto& p : cloud.points) {
                if (std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z)) finite.push_back(p);
                else ++nonfinite;
            }
            ++scans; points += finite.size(); rawPoints += packet.data.point_num;
            state = packet.data.state;
            dirtySum += state.dirty_index;
            dirtyMin = std::min(dirtyMin, double(state.dirty_index));
            dirtyMax = std::max(dirtyMax, double(state.dirty_index));
            tempMin = std::min(tempMin, double(state.apd_temperature));
            tempMax = std::max(tempMax, double(state.apd_temperature));
            lostUpMax = std::max(lostUpMax, double(state.packet_lost_up));
            lostDownMax = std::max(lostDownMax, double(state.packet_lost_down));
            window.push_back({elapsed, std::move(finite)});
            while (!window.empty() && elapsed - window.front().time > 1) window.pop_front();
            if (Clock::now() - lastPrint >= std::chrono::seconds(5)) {
                std::cout << std::fixed << std::setprecision(1) << elapsed << " s: " << scans << " scans, " << points
                          << " valid points, " << badCRC << " CRC errors, dirty index " << state.dirty_index << "\n" << std::flush;
                lastPrint = Clock::now();
            }
        }
        close(fd);
        if (!scans) throw std::runtime_error("No valid 3D scan packets received");
        const double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
        // Use the complete observation window, including any initial wait.
        const double rate = scans / elapsed;
        size_t snapshotPoints = 0;
        for (const auto& b : window) snapshotPoints += b.points.size();
        std::ofstream ply(out / "scan.ply");
        ply << "ply\nformat ascii 1.0\ncomment Unitree L2; official SDK calibration; metres; latest one second; stationary accumulation\n"
            << "element vertex " << snapshotPoints << "\nproperty float x\nproperty float y\nproperty float z\nproperty uchar intensity\nend_header\n";
        ply << std::fixed << std::setprecision(5);
        for (const auto& b : window) for (const auto& p : b.points) ply << p.x << ' ' << p.y << ' ' << p.z << ' ' << int(p.intensity) << '\n';
        std::ofstream report(out / "health.json");
        report << std::fixed << std::setprecision(5)
            << "{\n  \"source_ip\": \"192.168.1.62\",\n  \"receiver_ip\": \"192.168.1.2\",\n"
            << "  \"duration_s\": " << elapsed << ",\n  \"received_packets\": " << packets
            << ",\n  \"first_packet_s\": " << firstData << ",\n  \"last_packet_s\": " << lastData
            << ",\n  \"valid_scan_packets\": " << scans << ",\n  \"scan_packets_per_s\": " << rate
            << ",\n  \"raw_points\": " << rawPoints << ",\n  \"valid_points\": " << points
            << ",\n  \"valid_points_per_s\": " << (rawPoints ? rate * points / scans : 0)
            << ",\n  \"bad_frame\": " << badFrame << ",\n  \"bad_crc\": " << badCRC << ",\n  \"bad_payload\": " << badPayload
            << ",\n  \"nonfinite_points\": " << nonfinite << ",\n  \"sequence_gaps\": " << seqGaps
            << ",\n  \"sequence_resets_or_reorder\": " << seqResets << ",\n  \"duplicate_sequences\": " << duplicates
            << ",\n  \"normal_1024_sequence_wraps\": " << seqWraps
            << ",\n  \"dirty_index_mean\": " << dirtySum / scans << ",\n  \"dirty_index_min\": " << dirtyMin << ",\n  \"dirty_index_max\": " << dirtyMax
            << ",\n  \"apd_temperature_min_c\": " << tempMin << ",\n  \"apd_temperature_max_c\": " << tempMax
            << ",\n  \"device_packet_lost_up_max\": " << lostUpMax << ",\n  \"device_packet_lost_down_max\": " << lostDownMax
            << ",\n  \"rotation_periods_raw\": [" << state.sys_rotation_period << ',' << state.com_rotation_period << "]"
            << ",\n  \"snapshot_points\": " << snapshotPoints << ",\n  \"packet_types\": {";
        bool comma = false;
        for (const auto& item : types) { if (comma) report << ','; report << '"' << item.first << "\":" << item.second; comma = true; }
        report << "}\n}\n";
        if (!ply || !report) throw std::runtime_error("Could not write capture output");
        std::cout << "Wrote " << snapshotPoints << " snapshot points and health report to " << out << '\n';
        return (badFrame || badCRC || badPayload || nonfinite) ? 2 : 0;
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
