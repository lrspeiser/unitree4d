/* Copyright (c) 2024, Unitree Robotics; Copyright (c) 2026, Leonard Speiser.
 * Calibration math adapted from unilidar_sdk2/unitree_lidar_utilities.h.
 * Distributed under the BSD 3-Clause license; see LICENSE and THIRD_PARTY.md. */
package unitree4d;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.zip.CRC32;

/** Decoder for observed L2 Ethernet 3D scan packets. Distances are metres. */
public final class L2PacketDecoder {
  public static final int PACKET_BYTES = 1044;

  /** A single ~4.6 ms scan slice, not a full revolution. xyzi is x,y,z,intensity. */
  public record Scan(long sequence, long sensorSeconds, long sensorNanos,
      long receivedAtNanos, float[] xyzi, float dirtyIndex, float apdTemperatureC,
      float deviceLostUp, float deviceLostDown) {
    public int pointCount() { return xyzi.length / 4; }
    public double ageSeconds(long nowNanos) { return (nowNanos - receivedAtNanos) * 1e-9; }
    public double nearestReturnMeters() {
      double nearest = Double.POSITIVE_INFINITY;
      for (int i = 0; i < xyzi.length; i += 4) {
        nearest = Math.min(nearest, Math.sqrt(xyzi[i] * (double) xyzi[i]
            + xyzi[i + 1] * (double) xyzi[i + 1] + xyzi[i + 2] * (double) xyzi[i + 2]));
      }
      return nearest;
    }
  }

  private static void require(boolean condition, String reason) {
    if (!condition) throw new IllegalArgumentException(reason);
  }

  public Scan decode(byte[] data, int length, long receivedAtNanos) {
    require(length == PACKET_BYTES && data.length >= length, "Expected 1044-byte 3D packet");
    ByteBuffer b = ByteBuffer.wrap(data, 0, length).order(ByteOrder.LITTLE_ENDIAN);
    require(b.getInt(0) == 0x0a05aa55, "Header magic");
    require(b.getInt(4) == 102 && b.getInt(8) == length, "Packet type or length");
    require(data[length - 2] == 0 && Byte.toUnsignedInt(data[length - 1]) == 255, "Tail magic");
    CRC32 crc = new CRC32();
    crc.update(data, 12, length - 24); // Verified wire CRC: payload only.
    require(crc.getValue() == Integer.toUnsignedLong(b.getInt(length - 12)), "Payload CRC");
    require(b.getInt(16) == 1020, "Payload size");
    long nanos = Integer.toUnsignedLong(b.getInt(24));
    require(nanos < 1_000_000_000L, "Sensor nanoseconds");
    int count = b.getInt(128);
    require(count >= 0 && count <= 300, "Point count");
    for (int offset = 36; offset < 128; offset += 4) {
      require(Float.isFinite(b.getFloat(offset)), "Nonfinite calibration or telemetry");
    }
    double a = b.getFloat(64), axisB = b.getFloat(68);
    double thetaBias = b.getFloat(72), alphaBias = b.getFloat(76);
    double beta = b.getFloat(80), xi = b.getFloat(84);
    double rangeBias = b.getFloat(88), scale = b.getFloat(92);
    double thetaStart = b.getFloat(96) + thetaBias, thetaStep = b.getFloat(100);
    double rangeMin = Math.max(0.05, b.getFloat(108)), rangeMax = b.getFloat(112);
    double alphaStart = b.getFloat(116) + alphaBias, alphaStep = b.getFloat(120);
    require(scale > 0 && rangeMax >= rangeMin && rangeMax <= 1000, "Range calibration");
    float[] points = new float[count * 4];
    int used = 0;
    double sinBeta = Math.sin(beta), cosBeta = Math.cos(beta);
    double sinXi = Math.sin(xi), cosXi = Math.cos(xi);
    for (int i = 0; i < count; i++) {
      int raw = Short.toUnsignedInt(b.getShort(132 + i * 2));
      if (raw == 0) continue;
      double range = scale * (raw + rangeBias);
      if (range < rangeMin || range > rangeMax) continue;
      double alpha = alphaStart + i * alphaStep, theta = thetaStart + i * thetaStep;
      double sinAlpha = Math.sin(alpha), cosAlpha = Math.cos(alpha);
      double partA = (-cosBeta * sinXi + sinBeta * cosXi * sinAlpha) * range + axisB;
      double partB = cosAlpha * cosXi * range;
      double partC = (sinBeta * sinXi + cosBeta * cosXi * sinAlpha) * range;
      float x = (float) (Math.cos(theta) * partA - Math.sin(theta) * partB);
      float y = (float) (Math.sin(theta) * partA + Math.cos(theta) * partB);
      float z = (float) (partC + a);
      require(Float.isFinite(x) && Float.isFinite(y) && Float.isFinite(z), "Nonfinite point");
      points[used++] = x; points[used++] = y; points[used++] = z;
      points[used++] = Byte.toUnsignedInt(data[732 + i]);
    }
    return new Scan(Integer.toUnsignedLong(b.getInt(12)),
        Integer.toUnsignedLong(b.getInt(20)), nanos, receivedAtNanos,
        Arrays.copyOf(points, used), b.getFloat(36), b.getFloat(48), b.getFloat(40), b.getFloat(44));
  }
}
