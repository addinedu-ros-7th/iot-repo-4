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
DHT11 dht(DHT_PIN);  // Pass the DHT_PIN to the constructor

// LED SETUP
const int R = A2;
const int B = A1;
const int G = A0;

// SUN WATERLEVEL SENSOR
const int WATERLEVEL_PIN = A4;

// VARIABLE SETUP
int LEE_temperature = 0;
int LEE_humidity = 0;
int SUN_water_level = 0;

bool isCoolingPenActive = false;
bool isServoActive = false;
bool systemActivate = false;
int input = 0;

void setup() {
  pinMode(MOTOR_PIN_A_A, OUTPUT);
  pinMode(MOTOR_PIN_A_B, OUTPUT);
  pinMode(MOTOR_PIN_B_A, OUTPUT);
  pinMode(MOTOR_PIN_B_B, OUTPUT);
  pinMode(R, OUTPUT);
  pinMode(G, OUTPUT);
  pinMode(B, OUTPUT);

  servo_pin_A.attach(6);
  servo_pin_B.attach(7);

  Serial.begin(9600);
}

void loop() {
  LEE_humidity = dht.readHumidity();  // Read humidity
  LEE_temperature = dht.readTemperature();  // Read temperature
  SUN_water_level = analogRead(WATERLEVEL_PIN);

  Serial.print("Humidity: ");
  Serial.print(LEE_humidity);
  Serial.print(", Temperature: ");
  Serial.print(LEE_temperature);
  Serial.print(", Water Level: ");
  Serial.print(SUN_water_level);

  Serial.println();

  delay(1000);

  // AUTOMATION SETUP 
  if (Serial.available() > 0) { // Writeread()
    input = Serial.parseInt(); // Read input as an integer
    isCoolingPenActive = true;
    isServoActive = true;

    coolingPen();
    servoMotor();
    RGB_color();
  } else {
    //Serial.println("Serial Error");
  }
}

// Function Setup
void coolingPen() {
  if (input > 20 && input < 23 || input == 51) {
    systemActivate = true;
    analogWrite(MOTOR_PIN_A_A, 30);
    analogWrite(MOTOR_PIN_A_B, 0);
    analogWrite(MOTOR_PIN_B_A, 30);
    analogWrite(MOTOR_PIN_B_B, 0);
  } else if (input > 23 && input < 25 || input == 52) {
    systemActivate = true;
    analogWrite(MOTOR_PIN_A_A, 100);
    analogWrite(MOTOR_PIN_A_B, 0);
    analogWrite(MOTOR_PIN_B_A, 100);
    analogWrite(MOTOR_PIN_B_B, 0);
  } else if (input > 25 || input == 53) {
    systemActivate = true;
    analogWrite(MOTOR_PIN_A_A, 250);
    analogWrite(MOTOR_PIN_A_B, 0);
    analogWrite(MOTOR_PIN_B_A, 250);
    analogWrite(MOTOR_PIN_B_B, 0);
  } else if (input == 0) {
    systemActivate = false;
    analogWrite(MOTOR_PIN_A_A, 0);
    analogWrite(MOTOR_PIN_A_B, 0);
    analogWrite(MOTOR_PIN_B_A, 0);
    analogWrite(MOTOR_PIN_B_B, 0);
  }
}

void servoMotor() {
  if (input > 20 && input < 23 || input == 51) {
    systemActivate = true;
    servo_pin_A.write(60);
    servo_pin_B.write(60);
  } else if (input > 23 && input < 25 || input == 52) {
    systemActivate = true;
    servo_pin_A.write(120);
    servo_pin_B.write(120);
  } else if (input > 25 || input == 53) {
    systemActivate = true;
    servo_pin_A.write(180);
    servo_pin_B.write(180);
  } else if (input == 0) {
    systemActivate = false;
    servo_pin_A.write(0);
    servo_pin_B.write(0);
  }
}

void RGB_color() {
  if (input > 1 && input < 10 || input == 61) {
    systemActivate = true;
    analogWrite(R, 0); // Set RGB to Green
    analogWrite(G, 255);
    analogWrite(B, 0);
  } else if (input > 10 && input < 15 || input == 62) {
    systemActivate = true;
    analogWrite(R, 0); // Set RGB to Cyan
    analogWrite(G, 255);
    analogWrite(B, 255);
  } else if (input > 15 && input < 20 || input == 63) {
    systemActivate = true;
    analogWrite(R, 255); // Set RGB to Red
    analogWrite(G, 0);
    analogWrite(B, 0);
  } else if (input == 0) {
    systemActivate = false;
    analogWrite(R, 255); // Set RGB to White
    analogWrite(G, 255);
    analogWrite(B, 255);
  }
}
