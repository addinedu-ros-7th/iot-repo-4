#include <SPI.h>           // SPI 통신 라이브러리 포함
#include <MFRC522.h>       // RFID 모듈 MFRC522 제어 라이브러리 포함
#include <List.hpp>        // 리스트 구조를 제공하는 라이브러리 포함

#define RST_PIN         9          // 리셋 핀 설정
#define SS_PIN          10         // SS(슬레이브 선택) 핀 설정
#define BUZZER          8          // 부저 핀 설정
#define led             7          // led설정

List<MFRC522::Uid> tag_list;       // UID 정보를 저장하는 리스트 생성


bool gyro_moved = false;          // 자이로 센서가 움직이면

MFRC522 mfrc522(SS_PIN, RST_PIN);  // RFID 모듈 인스턴스 생성

unsigned long lastBuzzTime = 0;      // 마지막으로 부저가 울린 시간
unsigned long lastCardCheckTime = 0; // 마지막으로 카드 확인을 시도한 시간
unsigned long lastLogSentTime = 0;  // 마지막으로 로그를 보낸 시간

const unsigned long logSendInterval = 2000; // 로그 보냄 간격 (밀리초)
const unsigned long buzzInterval = 1000; // 부저 울림 간격 (밀리초)
const unsigned long cardCheckInterval = 500; // 카드 확인 간격 (밀리초)

int arduinoState = 0;// 0이면 전체 꺼짐, 1이면 부저 울림 전체 꺼짐, 2면 부저 안울림 전체 켜짐

void setup() {
	Serial.begin(9600);	          // 시리얼 통신 시작 (속도: 9600 bps)
	while (!Serial);              // 시리얼 포트가 열릴 때까지 대기
	SPI.begin();                  // SPI 버스 초기화
	mfrc522.PCD_Init();           // RFID 리더기 초기화
    pinMode(BUZZER, OUTPUT);
	delay(4);                     // 초기화 후 대기 (보드에 따라 필요할 수 있음)
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
          Serial.println("buzzing");
          lastBuzzTime = currentMillis;  // 마지막 부저 시간 갱신
        }


      //led를 끔
      
    }
    
    if (arduinoState == 2){//----------------------------------------------------- 아두이노 상태가 2이라면

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
