#include <Wire.h>

const int MPU_1 = 0x68;  // 중간층 (0.4)
const int MPU_2 = 0x69;  // 상층 (0.9)

void setup() {
  Wire.begin();
  Serial.begin(9600);

  // MPU 초기화
  Wire.beginTransmission(MPU_1);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);

  Wire.beginTransmission(MPU_2);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);
}

void loop() {
  int16_t AcX_1, AcZ_1, AcX_2, AcZ_2;

  // ===== 중간층 센서 =====
  Wire.beginTransmission(MPU_1);
  Wire.write(0x3B); // AcX High부터 시작
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_1, 6, true);

  AcX_1 = Wire.read() << 8 | Wire.read(); // AcX
  Wire.read(); Wire.read();               // AcY skip
  AcZ_1 = Wire.read() << 8 | Wire.read(); // AcZ

  // ===== 상층 센서 =====
  Wire.beginTransmission(MPU_2);
  Wire.write(0x3B); // AcX High부터 시작
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_2, 6, true);

  AcX_2 = Wire. read() << 8 | Wire.read(); // AcX
  Wire.read(); Wire.read();               // AcY skip
  AcZ_2 = Wire.read() << 8 | Wire.read(); // AcZ

  // ===== 송신 (총 8바이트: AcX_1, AcZ_1, AcX_2, AcZ_2) =====
  Serial.write((uint8_t*)&AcX_1, 2);
  Serial.write((uint8_t*)&AcZ_1, 2);
  Serial.write((uint8_t*)&AcX_2, 2);
  Serial.write((uint8_t*)&AcZ_2, 2);

  delay(100);
}