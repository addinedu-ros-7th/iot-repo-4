
![system_architecture](https://github.com/user-attachments/assets/7bf3d637-bb49-4fa9-bd7a-8d599a98806e)

***

## 🌱 개요

이 프로젝트는 아두이노로 스마트 농업 시스템을 재현하기 위해 개발된 작물 재배 자동화 및 모니터링 솔루션입니다.<br> 센서와 다양한 출력 장치들이 상호작용하여 실시간 데이터를 수집하고, <br > 
환경에 맞춘 자동화 작업을 수행하여,<br>
작물 재배 환경을 최적화하는 데 목표를 두고 있습니다.

<br>

<br>

***

## 📚 기술 스택


<div align=center> 
  <img src="https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white"> 
  <img src="https://img.shields.io/badge/c++-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white">
  <br>

  <img src="https://img.shields.io/badge/github-181717?style=for-the-badge&logo=github&logoColor=white">
  <img src="https://img.shields.io/badge/jira-0052CC?style=for-the-badge&logo=jira&logoColor=white">
  <img src="https://img.shields.io/badge/confluence-172B4D?style=for-the-badge&logo=confluence&logoColor=white">
  <img src="https://img.shields.io/badge/slack-4A154B?style=for-the-badge&logo=slack&logoColor=white">
  <br>
  
  <img src="https://img.shields.io/badge/arduino-00979D?style=for-the-badge&logo=arduino&logoColor=white">
  <img src="https://img.shields.io/badge/mysql-4479A1?style=for-the-badge&logo=mysql&logoColor=white"> 

  <br>
</div>


<br>

***

<br>

## ⚙️ 기능 명세

| **기능 유형**     | **기능**                              | **설명**                                                |
|--------------------|--------------------------------------------|---------------------------------------------------------|
| 센서 / DB  | 물통 수위 감지 및 업데이트                | 물통의 수위를 실시간으로 측정하고 DB에 업데이트            |
|                    | 배양액 수위 감지 및 업데이트              | 배양액의 수위를 실시간으로 측정하고 DB에 업데이트          |
|                    | 토양 습도 감지 및 업데이트                | 토양 습도를 실시간으로 감지하여 DB에 업데이트             |
|                    | 외부 온습도 감지                         | 외부 온습도를 실시간으로 감지하여 DB에 업데이트           |
|                    |  정상/비정상 싹 개수 업데이트  | 발아 상태별로 정상/비정상 싹을 탐지하여 개수를 DB에 업데이트 |
| 디스플레이  | 물통 수위 디스플레이                     | 식물에게 줄 물이 담긴 물통의 수위를 표시하여 관리자에게 제공 |
|                    | 배양액 수위 디스플레이                   | 식물에게 줄 배양액이 담긴 배양액 통의 수위를 표시하여 관리자에게 제공 |
|                    | 토양 습도 디스플레이                     | 토양의 습도를 표시하여 관리자에게 제공                  |
|                    | 외부 온습도 디스플레이                   | 외부 온습도 상태를 표시하여 관리자에게 제공              |
|                    | 발아 상태 디스플레이                     | 웹 캠을 통해 딥러닝으로 발아 상태별 정상/비정상 싹 개수를 탐지 및 표시하여 관리자에게 제공 |
| 알림       | 물통 수위 알림                           | 물통의 수위가 일정값 이하로 내려가면 관리자에게 물통 채우기 알림 전송 |
|                    | 배양액 수위 알림                         | 배양액의 수위가 일정값 이하로 내려가면 관리자에게 배양액 채우기 알림 전송 |
|                    | 주기적 상태 알림                        | 물 수위, 배양액 수위, 토양 습도, 외부 습도 및 온도 정보를 주기적으로 관리자에게 알림 전송 |
|                    | 로그인 알림                             | 관리자 로그인시 알림 전송                              |
| 액션      | 자동 물 공급                            | 자동으로 일정 시간마다 토양습도를 체크하여 습도가 일정 이하면 펌프를 통해 물을 공급하는 기능 |
|                    | 수동 물 공급                            | 수동으로 물을 공급하는 기능                            |
|                    | 자동 배양액 공급                        | 자동으로 일정 시간마다 배양액을 공급하는 기능             |
|                    | 수동 배양액 공급                        | 수동으로 배양액을 공급하는 기능                         |
|                    | 냉난방 자동 제어                        | 냉난방 자동 상태에서 온도에 따라 단계별로 냉난방을 적용하여 팬, 창문, 히터 LED를 작동시키는 기능 |
|                    | 냉난방 수동 제어                        | 수동으로 단계별 냉난방을 적용할 수 있는 기능             |
|                    | RFID 보안 상태 관리                    | RFID 태그로 보안 상태를 해지하거나 활성화하는 기능       |
|                    | 움직임 감지 보안 경보                  | 움직임 감지시 보안 경보 상태가 되며 경고하는 기능        |
|                    | 조명 LED 유지                          | 조명 LED를 상시 유지하는 기능                          |



<br>

***

<br>

## 🧩 시스템 아키텍처
<br>

![system_architecture](https://github.com/user-attachments/assets/89a47ec8-6b56-4385-8dec-177bcf8193af)

<br>

***

<br>

## 🖼️ 3D 설계
<br>

![3D_architecture](https://github.com/user-attachments/assets/3daa238a-8bbf-4430-9c6a-e8f8f3b1b478)

<br>

![3D_architecture2](https://github.com/user-attachments/assets/270f2bfd-e1f3-47aa-b826-ac5a7e903ea4)


<br>

***



## 📊 상태 다이어그램
<br>

![State Diagram](https://github.com/user-attachments/assets/8cf88e12-686f-4a50-be9f-6a50593f0a29)

<br>
<br>