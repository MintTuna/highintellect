#include <Servo.h>

Servo myServo;
int pos = 90; // 초기 위치를 90도로 설정 (중간값)

void setup() {
  Serial.begin(9600);       // 시리얼 통신 시작
  myServo.attach(9);        // 서보 제어 핀 설정 (PWM 핀 사용)
  myServo.write(pos);       // 초기 위치
  delay(500);
  Serial.println("시리얼에 1 또는 2를 입력하세요.");
}

void loop() {
  if (Serial.available() > 0) {
    char input = Serial.read();

    if (input == '1') {
      pos += 90;
      if (pos > 180) pos = 180;  // 범위 제한
      myServo.write(pos);
      Serial.print("현재 각도: ");
      Serial.println(pos);
    }

    else if (input == '2') {
      pos -= 90;
      if (pos < 0) pos = 0;      // 범위 제한
      myServo.write(pos);
      Serial.print("현재 각도: ");
      Serial.println(pos);
    }
  }
}