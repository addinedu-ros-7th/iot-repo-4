
![system_architecture](https://github.com/user-attachments/assets/7bf3d637-bb49-4fa9-bd7a-8d599a98806e)

[PPT 링크](https://docs.google.com/presentation/d/1ggPNrnSeVovyCdoah-VRCkFlJqgdLUMNempdSXxGVjI/edit?usp=sharing)

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

| 그룹        | 기능                     | 설명                                                      |
|-------------|--------------------------|-----------------------------------------------------------|
| 센서/DB     | 수위 감지 및 업데이트        | 물통의 수위를 실시간으로 측정하고 DB에 업데이트             |
|             | 수위 감지 및 업데이트        | 배양액의 수위를 실시간으로 측정하고 DB에 업데이트           |
|             | 습도 감지 및 업데이트        | 토양 습도를 실시간으로 감지하여 DB에 업데이트               |
|             | 외부 온습도 감지            | 외부 온습도를 실시간으로 감지하여 DB에 업데이트             |
|             | 발아 상태 감지             | 발아 상태별로 정상/비정상 싹을 탐지하여 개수를 DB에 업데이트               |
| 디스플레이  | 수위 디스플레이             | 물 수위를 GUI에 표시                                         |
|             | 배양액 수위 디스플레이       | 배양액 수위를 GUI에 표시                                  |
|             | 토양 습도 디스플레이        | 토양 습도를 GUI에 표시                                    |
|             | 외부 온습도 디스플레이       | 외부 온습도 상태를 GUI에 표시                              |
|             | 발아 상태 디스플레이        | 웹 캠을 통해 딥러닝으로 발아 상태별 정상/비정상 싹 개수를 탐지하여 GUI에 표시             |
| 알림        | 수위 알림                 | 수위가 일정값 이하로 내려가면 슬랙과 GUI로 물 채우기 알림 전송 |
|             | 배양액 수위 알림            | 수위가 일정값 이하로 내려가면 슬랙과 GUI로 배양액 채우기 알림 전송 |
|             | 실시간 상태 알림 전송       | 물 수위, 배양액 수위, 토양 습도, 외부 습도 및 온도 정보 실시간으로 슬랙 전송 |
| 액션        | 자동 물 공급               | GUI에서 선택된 일정 시간마다 펌프를 통해 물을 공급          |
|             | 수동 물 공급               | GUI를 통해 수동으로 물을 공급하는 기능                     |
|             | 자동 배양액 공급            | GUI에서 선택된 일정 시간마다 펌프를 통해 배양액을 공급       |
|             | 수동 배양액 공급            | GUI를 통해 수동으로 배양액을 공급하는 기능                 |
|             | 자동 토양 습도 조절         | 지정된 시간마다 토양 습도값에 따라 자동으로 물을 공급하는 기능 |
|             | 온도에 따른 팬 자동 작동     | 온도에 따라 팬 1,2,3단계 작동                              |
|             | 자동 창문 열기 제어          | 온도가 높을 경우 창문이 열림                               |
|             | 자동 히터 LED 제어          | 온도에 따라 히터 LED 1, 2, 3단계 작동                     |
|             | 냉 난방 시스템 제어         | gui를 통해 자동, 수동 냉방 1, 2, 3단계 , 수동 히터 1, 2, 3단계를 적용하는 기능|
|             | 보안 관리                 | RFID 태그로 보안 상태 변경 가능                             |
|             | 자이로센서 기반 보안 제어     | 움직임 감지 시 보안 상태로 전환하며 부저 울림               |
|             | 광원 LED 상시 켜짐          | 광원 LED를 유지 시켜둠                                     |



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

<br>


## 🔧 메인 시스템 구성
<br>

![image](https://github.com/user-attachments/assets/d6e71f1a-5d10-4d5f-991a-2195dd46a361)

<br>
<br>

## 🖥️ GUI 구성
<br>

![image](https://github.com/user-attachments/assets/ca40582b-0c25-4de2-8e1d-3441d7378a72)
<br>
<br>

## 🖥️ AI 모델 활용
<br>

![image](https://github.com/user-attachments/assets/da651389-c790-450b-b913-529dbcdd8929)

![image](https://www.aihub.or.kr/web-nas/aihub21/files/editor/2023/05/693152addd4246faa11978e8a73f3912.png)
<br>
<br>

## 🎥 시연 영상

[![시연 영상](https://github.com/user-attachments/assets/dda7faec-7499-4395-bfb8-710bbabb7a9c)](https://drive.google.com/file/d/12uW_B-E1xBmYg843od77IKQixIxkJizn/view?usp=sharing)


