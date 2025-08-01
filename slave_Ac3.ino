#include <Wire.h>
#include <Arduino.h>

const int MPU_3 = 0x68; // 수신 아두이노에 연결한 MPU6050

void setup() {
  Serial.begin(9600);  // 송신 아두이노와 동일 속도
  Wire.begin();        // I2C 초기화
  // MPU6050 초기화 (PWR_MGMT_1 = 0)
  Wire.beginTransmission(MPU_3);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);
}

void loop() {
  int16_t AcX_3 = 0, AcZ_3 = 0;

  // ===== AcX_3, AcZ_3 읽기 =====
  Wire.beginTransmission(MPU_3);
  Wire.write(0x3B);  // AcX High부터 시작
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_3, 6, true);  // AcX(2) + AcY(2) + AcZ(2) = 6바이트

   if (Wire.available() >= 6) {
    AcX_3 = Wire.read() << 8 | Wire.read(); // AcX
    Wire.read(); Wire.read();               // AcY skip
    AcZ_3 = Wire.read() << 8 | Wire.read(); // AcZ
  }
  // ===== 송신 아두이노로부터 데이터 수신 =====
  if (Serial.available() >= 8) {
    byte buffer[8];
    Serial.readBytes(buffer, 8);

    int16_t AcX_1 = buffer[0] | (buffer[1] << 8);
    int16_t AcZ_1 = buffer[2] | (buffer[3] << 8);
    int16_t AcX_2 = buffer[4] | (buffer[5] << 8);
    int16_t AcZ_2 = buffer[6] | (buffer[7] << 8);

    Serial.print(AcX_1); Serial.print(",");
    Serial.print(AcZ_1); Serial.print(",");
    Serial.print(AcX_2); Serial.print(",");
    Serial.print(AcZ_2); Serial.print(",");
    Serial.print(AcX_3); Serial.print(",");
    Serial.println(AcZ_3);

    delay(100);

  }
}