
#include <SPI.h>           // SPI 통신 라이브러리 포함
#include <MFRC522.h>       // RFID 모듈 MFRC522 제어 라이브러리 포함
#include <Wire.h>          // I2C 통신을 위한 라이브러리

#define RST_PIN         9          // 리셋 핀 설정
#define SS_PIN          10         // SS(슬레이브 선택) 핀 설정
#define BUZZER          8          // 부저 핀 설정
#define led             7          // led설정


const int MPU=0x68; 
int16_t AcX, AcY, AcZ, Tmp, GyX, GyY, GyZ; // Ac: 가속도, Gy: 자이로

bool gyro_moved = false;          // 자이로 센서가 움직이면


unsigned long lastBuzzTime = 0;      // 마지막으로 부저가 울린 시간
unsigned long lastCardCheckTime = 0; // 마지막으로 카드 확인을 시도한 시간
unsigned long lastLogSentTime = 0;  // 마지막으로 로그를 보낸 시간
unsigned long lastSerialInputTime = 0; // 마지막으로 Serial 입력이 있었던 시간

const unsigned long logSendInterval = 1000; // 로그 보냄 간격 (밀리초)
const unsigned long buzzInterval = 1000; // 부저 울림 간격 (밀리초)
const unsigned long cardCheckInterval = 500; // 카드 확인 간격 (밀리초)
const unsigned long serialTimeout = 5000; // Serial 입력 타임아웃 시간 (5초)

int arduinoState = 0; // 0이면 전체 꺼짐, 1이면 부저 울림 전체 꺼짐, 2면 부저 안울림 전체 켜짐

void setup() {
  Serial.begin(9600); // 시리얼 통신 시작 (속도: 9600 bps)
  while (!Serial); // 시리얼 포트가 열릴 때까지 대기
  SPI.begin(); // SPI 버스 초기화
  mfrc522.PCD_Init(); // RFID 리더기 초기화
  pinMode(BUZZER, OUTPUT);
  pinMode(led, OUTPUT);
  Wire.begin(); // I2C 초기화
  Wire.beginTransmission(MPU);
  Wire.write(0x6B);  
  Wire.write(0);    
  Wire.endTransmission(true);  // MPU 초기화
  delay(4); // 초기화 후 대기 (보드에 따라 필요할 수 있음)
}

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - lastLogSentTime >= logSendInterval){   // 로그를 보내고 나서 n 초가 경과했을 경우
    Serial.print("Security: "); // 로그를 보냄
    Serial.println(arduinoState);
    lastLogSentTime = currentMillis;
  }

  // 5초간 Serial 입력이 없을 경우 전체 꺼짐 상태로 전환
  if (currentMillis - lastSerialInputTime >= serialTimeout && arduinoState != 0) {
    arduinoState = 0;
  }

  if (Serial.available()){ // 인풋이 왔을 경우
    int input = Serial.parseInt(); // 입력된 값을 정수로 파싱
    if (input >= 0) { // 유효한 값만 처리
      arduinoState = input; // 상태 업데이트
      lastSerialInputTime = currentMillis; // 마지막 입력 시간 갱신
    }
  }

  
  // 상태에 따른 동작
  if (arduinoState == 0) { 
    // LED 끔
    digitalWrite(led, LOW);
    // 부저 끔
    noTone(BUZZER);
  } else if (arduinoState == 1) {
    if (currentMillis - lastBuzzTime >= buzzInterval) { // 부저를 울림 
      tone(BUZZER, 523, 100); // 부저 소리 발생
      Serial.println("buzzing");
      lastBuzzTime = currentMillis;  // 마지막 부저 시간 갱신
    }
    // LED 끔
    digitalWrite(led, LOW);
  } else if (arduinoState == 2) {
    // LED 켬
    digitalWrite(led, HIGH);
  }

  // 카드 확인을 지정된 간격마다 수행
  if (currentMillis - lastCardCheckTime >= cardCheckInterval) {
    lastCardCheckTime = currentMillis; // 마지막 카드 확인 시간 갱신

    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
      if (arduinoState == 0) {
        arduinoState = 2; // 상태를 2로 변경
      }
      if (arduinoState == 1) {
        arduinoState = 0; // 상태를 0으로 변경
      }
      if (arduinoState == 2) {
        arduinoState = 0; // 상태를 0으로 변경
      }
      // 가드 상태에서 카드가 감지되면 상태 변경
      gyro_moved = false;
    }
  }
}

void loop() {
    unsigned long currentMillis = millis();
     if (currentMillis - lastLogSentTime >= logSendInterval) {
      Serial.print("Security: ");
      Serial.println(arduinoState);
      lastLogSentTime = currentMillis;
     }


    if (Serial.available()){                                  // 인풋을 받음
      int input = Serial.parseInt();                        // 인풋을 인트로 파싱함.
      arduinoState = input;
    }
    if (arduinoState == 0){//----------------------------------------------------- 아두이노 상태가 0이라면

      //led를 끔

    }


    if (arduinoState == 1){//----------------------------------------------------- 아두이노 상태가 1이라면
      if (currentMillis - lastBuzzTime >= buzzInterval) { // 부저를 울림 
          tone(BUZZER, 523, 100);         // 부저 소리 발생
          
          lastBuzzTime = currentMillis;  // 마지막 부저 시간 갱신
        }


      //led를 끔
      
    }
    
    if (arduinoState == 2){//----------------------------------------------------- 아두이노 상태가 2이라면

      // 자이로 값 읽기
      Wire.beginTransmission(MPU);
      Wire.write(0x3B);  
      Wire.endTransmission(false);
      Wire.requestFrom(MPU, 12, true);

      GyX = Wire.read() << 8 | Wire.read();
      GyY = Wire.read() << 8 | Wire.read();
      GyZ = Wire.read() << 8 | Wire.read();

      // 자이로 변화가 일정 threshold를 넘으면 움직였다고 판단
      if (abs(GyX) > 50 || abs(GyY) > 50 || abs(GyZ) > 50) {
        gyro_moved = true;
        arduinoState = 1;
      }

      //led를 켬
    }

    // 카드 확인을 지정된 간격마다 수행
    if (currentMillis - lastCardCheckTime >= cardCheckInterval) {
        lastCardCheckTime = currentMillis; // 마지막 카드 확인 시간 갱신

        // 새 카드가 리더기 범위에 있는지 확인
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
            if (arduinoState == 0){//----------------------------------------------------- 아두이노 상태가 0이라면
              arduinoState = 2;//상태를 2으로 변경
              Serial.print("Security: ");
              Serial.println(arduinoState);
            }
            else if (arduinoState == 1){//----------------------------------------------------- 아두이노 상태가 1이라면
              arduinoState = 0;//상태를 0으로 변경
              Serial.print("Security: ");
              Serial.println(arduinoState);
            }
            else if (arduinoState == 2){//----------------------------------------------------- 아두이노 상태가 2이라면
              arduinoState = 0;//상태를 0으로 변경
              Serial.print("Security: ");
              Serial.println(arduinoState);
            }
            gyro_moved = false;
            
        }
    }
}
