#include <fstream>
#include <iomanip>
#include "unitree_lidar_utilities.h"

int main(int argc, char** argv) {
  if (argc != 2) return 1;
  std::ifstream file(argv[1], std::ios::binary);
  unilidar_sdk2::LidarPointDataPacket packet{};
  file.read(reinterpret_cast<char*>(&packet), sizeof(packet));
  if (file.gcount() != sizeof(packet) || packet.data.point_num > 300) return 2;
  unilidar_sdk2::PointCloudUnitree cloud;
  unilidar_sdk2::parseFromPacketToPointCloud(cloud, packet, false, 0.05f, 1000.f);
  std::cout << std::setprecision(9);
  for (const auto& p : cloud.points) {
    std::cout << p.x << ',' << p.y << ',' << p.z << ',' << p.intensity << '\n';
  }
}
