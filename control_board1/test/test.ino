#include <DHT11.h>
#include <Servo.h>

// PIN SETUP
const int MOTOR_PIN_A_A = 5;
const int MOTOR_PIN_A_B = 4;
const int MOTOR_PIN_B_A = 3;
const int MOTOR_PIN_B_B = 2;

Servo servo_pin_A;
Servo servo_pin_B;

// DHT11 SENSOR
const int DHT_PIN = 13;
DHT11 dht(DHT_PIN);

// LED SETUP
const int R = A2;
const int B = A1;
const int G = A0;

// WATER/NUTRI LEVEL SENSOR
const int WATERLEVEL_PIN = A3;
const int NUTRIWATERLEVEL_PIN = A4;

// Moisture
const int MOISTURE_PIN = A5;

// Pump
const int WATER_PUMP_AA = 9;
const int WATER_PUMP_AB = 10;
const int NUTRI_PUMP_BA = 11;
const int NUTRI_PUMP_BB = 12;

// millis SETTING
unsigned long previousMillis = 0;   // 마지막으로 펌프 상태를 변경한 시간
const long onInterval = 10000;        // 3초동안 멈춤
const long offInterval = 3000;       // 1초동안 작동
bool pumpState = false;

// VARIABLE SETUP
int Temperature = 0;
int auto_Temperature = 0;
int Humidity = 0;
int Water_level = 0;
int Nutri_Water_level = 0;
int Moisture = 0;
int Moisture_mapped = 0;
bool isCoolingPenActive = false;
bool isServoActive = false;
bool systemActivate = false;
int dial_value = 0;

// 모터 단계별 조절
int level1_fan_motor_OUTPUT = 100;
int level2_fan_motor_OUTPUT = 150;
int level3_fan_motor_OUTPUT = 200;
int level1_servo_motor_OUTPUT = 45;
int level2_servo_motor_OUTPUT = 75;
int level3_servo_motor_OUTPUT = 100;

void setup() {
  pinMode(MOTOR_PIN_A_A, OUTPUT);
  pinMode(MOTOR_PIN_A_B, OUTPUT);
  pinMode(MOTOR_PIN_B_A, OUTPUT);
  pinMode(MOTOR_PIN_B_B, OUTPUT);
  pinMode(R, OUTPUT);
  pinMode(G, OUTPUT);
  pinMode(B, OUTPUT);
  pinMode(WATER_PUMP_AA, OUTPUT);
  pinMode(WATER_PUMP_AB, OUTPUT);
  pinMode(NUTRI_PUMP_BA, OUTPUT);
  pinMode(NUTRI_PUMP_BB, OUTPUT);
  servo_pin_A.attach(8);
  servo_pin_B.attach(6);
  Serial.begin(9600);
}

void loop() {
  Temperature = dht.readTemperature();
  Humidity = dht.readHumidity();
  Water_level = analogRead(WATERLEVEL_PIN);
  Nutri_Water_level = analogRead(NUTRIWATERLEVEL_PIN);
  Moisture = analogRead(MOISTURE_PIN);
  Moisture_mapped = map(Moisture, 0, 1023, 0, 100);

  // Pump Automation
  waterPump();
  //nutriPump();

  Serial.print("Humidity: ");
  Serial.print(Humidity);
  Serial.print(", Temperature: ");
  Serial.print(Temperature);
  Serial.print(", Water Level: ");
  Serial.print(Water_level);
  Serial.print(", Nutrition Water Level: ");
  Serial.print(Nutri_Water_level);
  Serial.print(", Moisture: ");
  Serial.print(Moisture_mapped);
  Serial.println();

  if (Serial.available() > 0){
    dial_value = Serial.parseInt();
    Serial.print(dial_value);
      // 디아얼 값 7 (자동)
    if (dial_value == 7){
      // 1단계
      auto_Temperature = Temperature;
      if (auto_Temperature > 20 && auto_Temperature <= 23){
        systemActivate = true;
        Serial.print(1111);
        level1();
        auto_Temperature = Temperature;
      }
      // 2단계
      
      else if (auto_Temperature > 23 && auto_Temperature <= 25){
        systemActivate = true;
        Serial.print(Temperature);
        Serial.print(2222);
        level2();
        auto_Temperature = Temperature;

      }
      // 3단계
      else if (auto_Temperature > 25 && auto_Temperature < 30 ){
        systemActivate = true;
        Serial.print(2222);
        level3();
        auto_Temperature = Temperature;
      }
    }
    // 다이얼 값이 1단계, 2단계, 3단계 일때
    else if (dial_value == 1){
      systemActivate = true;
      level1();
    }
    else if (dial_value == 2){
      systemActivate = true;
      level2();
    }
    else if (dial_value == 3){
      systemActivate = true;
      level3();
    }
    // 다이얼 값이 4단계, 5단계, 6단계 일ㄸ
    else if (dial_value == 4){
      systemActivate = true;
      analogWrite(R, 0); // Set RGB to Green
      analogWrite(G, 255);
      analogWrite(B, 0);
      fan_servo_off();
    }
    else if (dial_value == 5){
      systemActivate = true;
      analogWrite(R, 0); // Set RGB to Cyan
      analogWrite(G, 255);
      analogWrite(B, 255);
      fan_servo_off();
    }
    else if (dial_value == 6){
      systemActivate = true;
      analogWrite(R, 255); // Set RGB to Red
      analogWrite(G, 0);
      analogWrite(B, 0);
      fan_servo_off();
    }
    else if (dial_value == 0){
      systemActivate = false;
      analogWrite(R, 0); // Set RGB to White
      analogWrite(G, 0);
      analogWrite(B, 0);
      fan_servo_off();
    }
    delay(2000);
  }
}

void waterPump() {
  unsigned long currentMillis = millis();  // 현재 시간 가져오기

  // 작동/정지 주기를 비교
  if (pumpState && currentMillis - previousMillis >= onInterval) {
    // 1초 동안 펌프를 켬
    digitalWrite(WATER_PUMP_AA, HIGH);
    digitalWrite(WATER_PUMP_AB, LOW);
    previousMillis = currentMillis;  // 마지막 시간 갱신
    pumpState = false;               // 상태 변경 (정지)
  }
  else if (!pumpState && currentMillis - previousMillis >= offInterval) {
    // 3초 동안 멈춤
    digitalWrite(WATER_PUMP_AA, LOW);
    digitalWrite(WATER_PUMP_AB, LOW);
    previousMillis = currentMillis;  // 마지막 시간 갱신
    pumpState = true;                // 상태 변경 (작동)
  }
}

void level1(){
    analogWrite(MOTOR_PIN_A_A, level1_fan_motor_OUTPUT);
    analogWrite(MOTOR_PIN_A_B, 0);
    analogWrite(MOTOR_PIN_B_A, level1_fan_motor_OUTPUT);
    analogWrite(MOTOR_PIN_B_B, 0);
    servo_pin_A.write(level1_servo_motor_OUTPUT);
    servo_pin_B.write(level1_servo_motor_OUTPUT);
    analogWrite(R, 0); // Set RGB to White
    analogWrite(G, 0);
    analogWrite(B, 0);

  }
void level2(){
  analogWrite(MOTOR_PIN_A_A, level2_fan_motor_OUTPUT);
  analogWrite(MOTOR_PIN_A_B, 0);
  analogWrite(MOTOR_PIN_B_A, level2_fan_motor_OUTPUT);
  analogWrite(MOTOR_PIN_B_B, 0);
  servo_pin_A.write(level2_servo_motor_OUTPUT);
  servo_pin_B.write(level2_servo_motor_OUTPUT);
  analogWrite(R, 0); // Set RGB to White
  analogWrite(G, 0);
  analogWrite(B, 0);
}
void level3(){
  analogWrite(MOTOR_PIN_A_A, level3_fan_motor_OUTPUT);
  analogWrite(MOTOR_PIN_A_B, 0);
  analogWrite(MOTOR_PIN_B_A, level3_fan_motor_OUTPUT);
  analogWrite(MOTOR_PIN_B_B, 0);
  servo_pin_A.write(level3_servo_motor_OUTPUT);
  servo_pin_B.write(level3_servo_motor_OUTPUT);
  analogWrite(R, 0); // Set RGB to White
  analogWrite(G, 0);
  analogWrite(B, 0);
}
void fan_servo_off(){
  analogWrite(MOTOR_PIN_A_A, 0);
  analogWrite(MOTOR_PIN_A_B, 0);
  analogWrite(MOTOR_PIN_B_A, 0);
  analogWrite(MOTOR_PIN_B_B, 0);
  servo_pin_A.write(0);
  servo_pin_B.write(0); 
}

// Additional functions remain unchanged.


// // Function Setup
// void coolingPen() {
//   if (dial_value > 20 && dial_value < 23 || dial_value == 1) {
//     systemActivate = true;
//     analogWrite(MOTOR_PIN_A_A, 100);
//     analogWrite(MOTOR_PIN_A_B, 0);
//     analogWrite(MOTOR_PIN_B_A, 100);
//     analogWrite(MOTOR_PIN_B_B, 0);
//   } else if (dial_value > 23 && dial_value < 25 || dial_value == 2) {
//     systemActivate = true;
//     analogWrite(MOTOR_PIN_A_A, 150);
//     analogWrite(MOTOR_PIN_A_B, 0);
//     analogWrite(MOTOR_PIN_B_A, 150);
//     analogWrite(MOTOR_PIN_B_B, 0);
//   } else if (dial_value > 25 || dial_value == 3) {
//     systemActivate = true;
//     analogWrite(MOTOR_PIN_A_A, 250);
//     analogWrite(MOTOR_PIN_A_B, 0);
//     analogWrite(MOTOR_PIN_B_A, 250);
//     analogWrite(MOTOR_PIN_B_B, 0);
//   } else if (dial_value == 0) {
//     systemActivate = false;
//     analogWrite(MOTOR_PIN_A_A, 0);
//     analogWrite(MOTOR_PIN_A_B, 0);
//     analogWrite(MOTOR_PIN_B_A, 0);
//     analogWrite(MOTOR_PIN_B_B, 0);
//   }
// }
// void servoMotor() {
//   if (dial_value > 20 && dial_value < 23 || dial_value == 1) {
//     systemActivate = true;
//     servo_pin_A.write(45);
//     servo_pin_B.write(45);
//   } else if (dial_value > 23 && dial_value < 25 || dial_value == 2) {
//     systemActivate = true;
//     servo_pin_A.write(70);
//     servo_pin_B.write(70);
//   } else if (dial_value > 25 || dial_value == 3) {
//     systemActivate = true;
//     servo_pin_A.write(100);
//     servo_pin_B.write(100);
//   } else if (dial_value == 0) {
//     systemActivate = false;
//     servo_pin_A.write(0);
//     servo_pin_B.write(0);
//   }
//     else if (dial_value == 4 || dial_value == 5 || dial_value == 6){
//       servo_pin_A.write(0);
//       servo_pin_B.write(0);
//     }
//   }

// void RGB_color() {


//   if (Temperature > 1 && Temperature < 10 || dial_value == 4) {
//     systemActivate = true;
//     analogWrite(R, 0); // Set RGB to Green
//     analogWrite(G, 255);
//     analogWrite(B, 0);
//     servo_pin_A.write(0);
//     servo_pin_B.write(0);
//   } else if (Temperature > 10 && Temperature < 15 || dial_value == 5) {
//     systemActivate = true;
//     analogWrite(R, 0); // Set RGB to Cyan
//     analogWrite(G, 255);
//     analogWrite(B, 255);
//     servo_pin_A.write(0);
//     servo_pin_B.write(0);
//   } else if (Temperature > 15 && Temperature < 20 || dial_value == 6) {
//     systemActivate = true;
//     analogWrite(R, 255); // Set RGB to Red
//     analogWrite(G, 0);
//     analogWrite(B, 0);
//     servo_pin_A.write(0);
//     servo_pin_B.write(0);
//   } else if (dial_value == 0) {
//     systemActivate = false;
//     analogWrite(R, 0); // Set RGB to White
//     analogWrite(G, 0);
//     analogWrite(B, 0);
//   }
// }
