import numpy as np
import pandas as pd
import cv2
import sys
import pymysql
import time
import threading

# PyQt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import uic
from pyqtgraph.Qt import QtCore
import pyqtgraph as pg

# Arduino Serial Communication
import serial
from serial import SerialException
import serial.tools
from serial.tools import list_ports

# 필수 모듈 import
import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from PyQt5.QtCore import Qt
import cv2
import numpy as np
from PyQt5 import uic
import cv2
import torch
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
from PyQt5.QtGui import QPixmap
import resources_rc  # 리소스 파일 import

import os
os.environ["QT_LOGGING_RULES"] = "*.debug=false"

from use_table import UserTable, SmartFarmTable

# 현재 스크립트의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))

# 상위 디렉토리의 경로
parent_dir = os.path.join(current_dir, '..', 'AI')

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(parent_dir))

import detect_1  # 수정된 detect_1.py 파일 가져오기 (객체 검출 기능을 구현한 모듈)

# PyQt Designer File
from PyQt5 import uic

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_file_path = os.path.join(current_dir, 'interface03.ui')

form_class = uic.loadUiType(ui_file_path)[0]

main_usd_port = "/dev/ttyACM0"  # "/dev/ttyACM0"
sub_usd_port =  "/dev/ttyACM1" # "/dev/ttyACM1"

# main_usd_port와 sub_usd_port를 사용하여 Arduino에 연결
print(f"Main USB Port: {main_usd_port}")
print(f"Sub USB Port: {sub_usd_port}")

# DeepLearing Thread
class DetectionThread(QThread):
    image_update = pyqtSignal(QImage)
    detection_data_update = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        # 객체 검출 옵션 설정 및 모델 초기화
        self.opt = detect_1.parse_opt()
        self.opt.weights = '../AI/best.pt'
        self.opt.source = 0
        self.opt.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.opt.imgsz = (512, 512)
        self.opt.conf_thres = 0.25
        self.opt.iou_thres = 0.45
        self.opt.classes = None
        self.opt.agnostic_nms = False
        self.opt.half = False

        # 모델 초기화
        self.model = detect_1.DetectMultiBackend(
            self.opt.weights,
            device=self.opt.device,
            dnn=self.opt.dnn,
            data=self.opt.data,
            fp16=self.opt.half
        )
        self.stride = self.model.stride
        self.names = self.model.names
        self.imgsz = detect_1.check_img_size(self.opt.imgsz, s=self.stride)

        # 웹캠 열기
        self.cap = cv2.VideoCapture(self.opt.source)
        self.is_running = True

    def run(self):
        while self.is_running:
            ret, frame = self.cap.read()  # 프레임 읽기
            if ret:
                # 프레임에 대해 객체 검출 수행
                results = self.detect_frame(frame)

                # 결과에서 검출된 이미지와 정보 가져오기
                if results:
                    result = results[0]  # 첫 번째 프레임 결과 사용
                    im0 = result['image']
                    detections = result['detections']  # 검출된 객체 정보

                    # 검출된 객체 정보를 배열 형태로 추출하여 시그널로 전달
                    self.detection_array = []
                    for detection in detections:
                        self.detection_array.append({
                            'bbox': detection['bbox'],
                            'confidence': detection['confidence'],
                            'class': detection['class'],
                            'label': detection['label']
                        })

                    # 시그널을 통해 검출된 객체 정보를 전달
                    self.detection_data_update.emit(self.detection_array)

                    # OpenCV 이미지를 PyQt 이미지로 변환하여 시그널로 전달
                    im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)  # BGR을 RGB로 변환
                    h, w, ch = im0.shape  # 이미지의 높이, 너비, 채널 정보
                    bytes_per_line = ch * w  # 한 줄당 바이트 수 계산
                    qt_image = QImage(im0.data, w, h, bytes_per_line, QImage.Format_RGB888)  # PyQt 이미지 생성
                    scaled_image = qt_image.scaled(640, 480, Qt.KeepAspectRatio)
                    self.image_update.emit(scaled_image)
            else:
                break

    def stop(self):
        self.is_running = False
        self.cap.release()
        self.quit()

    # 한 프레임에서 객체 검출 수행 메서드
    def detect_frame(self, frame):
        # 이미지 전처리
        img = cv2.resize(frame, self.imgsz)  # 입력 프레임 크기를 모델에 맞게 조정
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR -> RGB, HWC -> CHW 형식 변환
        img = np.ascontiguousarray(img)  # 배열을 연속된 메모리 배열로 만듦

        # 텐서 변환
        im = torch.from_numpy(img).to(self.opt.device)  # NumPy 배열을 텐서로 변환하고, 디바이스에 로드
        im = im.half() if self.opt.half else im.float()  # 8비트 -> FP16/32 형식 변환
        im /= 255  # 0 - 255를 0.0 - 1.0 범위로 정규화
        if len(im.shape) == 3:
            im = im[None]  # 배치 차원 추가

        # 모델을 통한 추론
        pred = self.model(im, augment=self.opt.augment, visualize=self.opt.visualize)

        # NMS(Non-Max Suppression) 적용
        pred = detect_1.non_max_suppression(
            pred,
            self.opt.conf_thres,
            self.opt.iou_thres,
            self.opt.classes,
            self.opt.agnostic_nms,
            max_det=self.opt.max_det
        )

        # 검출 결과 처리
        im0 = frame.copy()  # 원본 프레임 복사
        results = []
        for i, det in enumerate(pred):  # 이미지별로 결과 처리
            annotator = detect_1.Annotator(im0, line_width=self.opt.line_thickness, example=str(self.names))  # 박스 라벨링 도구
            detections = []
            if len(det):
                # 검출된 객체 박스 크기 조정
                det[:, :4] = detect_1.scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                # 객체 정보 수집
                for *xyxy, conf, cls in reversed(det):
                    if self.opt.hide_labels:
                        label = None
                    else:
                        label = f'{self.names[int(cls)]} {conf:.2f}' if not self.opt.hide_conf else f'{self.names[int(cls)]}'

                    annotator.box_label(xyxy, label, color=detect_1.colors(int(cls), True))  # 박스와 라벨 추가
                    detection = {
                        'bbox': [int(coord.item()) for coord in xyxy],  # 객체 박스 좌표
                        'confidence': float(conf.item()),  # 신뢰도
                        'class': int(cls.item()),  # 클래스 ID
                        'label': self.names[int(cls.item())]  # 클래스 이름
                    }
                    detections.append(detection)

            im0 = annotator.result()  # 주석 추가된 이미지 결과 얻기
            results.append({
                'image': im0,
                'detections': detections
            })

        return results


# 시리얼 통신을 위한 스레드 클래스
class SerialThread(QThread):
    # 시그널 정의
    main_data_received = pyqtSignal(str)
    sub_data_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, main_port, sub_port):
        super().__init__()
        self.main_usd_port = main_port
        self.sub_usd_port = sub_port
        self.is_running = True
        # 시리얼 포트 초기화
        self.arduinoMainData = serial.Serial(self.main_usd_port, 9600, timeout=0.1)
        self.arduinoSubData = serial.Serial(self.sub_usd_port, 9600, timeout=0.1)

    def run(self):
        last_received_time_main = time.time()
        last_received_time_sub = time.time()
        state1_start_time = None

        while self.is_running:
            current_time = time.time()

            # Arduino Sub 데이터 읽기
            try:
                if not self.arduinoSubData.is_open:
                    self.arduinoSubData.open()

                data2 = self.arduinoSubData.readline().decode("utf-8").strip()

                if data2:
                    print("data2: ", data2)
                    last_received_time_sub = current_time  # 데이터 수신 시간 갱신
                    self.sub_data_received.emit(data2)
                else:
                    # 빈 메시지가 5초 이상 지속되면 에러 메시지 출력
                    if current_time - last_received_time_sub > 20:
                        self.error_occurred.emit("Arduino Sub 데이터 수신 오류", "20초 이상 데이터를 받지 못했습니다.")

            except SerialException:
                self.error_occurred.emit("Arduino Sub 연결 끊어짐 오류", "Arduino Sub와의 연결이 끊어졌습니다.")
            except Exception as e:
                print(f"Unexpected error from Arduino Sub: {e}")

            # Arduino Main 데이터 읽기
            try:
                if not self.arduinoMainData.is_open:
                    self.arduinoMainData.open()

                data = self.arduinoMainData.readline().decode('utf-8').strip()

                if data:
                    print("data", data)
                    last_received_time_main = current_time  # 데이터 수신 시간 갱신
                    self.main_data_received.emit(data)
                else:
                    # 빈 메시지가 5초 이상 지속되면 에러 메시지 출력
                    if current_time - last_received_time_main > 20:
                        #self.error_occurred.emit("Arduino Main 데이터 수신 오류", "20초 이상 데이터를 받지 못했습니다.")
                        pass

            except SerialException:
                self.error_occurred.emit("Arduino Main 연결 끊어짐 오류", "Arduino Main과의 연결이 끊어졌습니다.")
            except Exception as e:
                print(f"Unexpected error from Arduino Main: {e}")

            time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.arduinoMainData.close()
        self.arduinoSubData.close()
        self.quit()


# Main Operating Window
class SunnyMainWindow(QMainWindow, form_class):
    def __init__(self):
        super(SunnyMainWindow, self).__init__()
        self.setupUi(self)
        # 시리얼 통신 스레드 생성
        self.serial_thread = SerialThread(main_usd_port, sub_usd_port)
        # 시그널 연결
        self.serial_thread.main_data_received.connect(self.handle_main_data)
        self.serial_thread.sub_data_received.connect(self.handle_sub_data)
        self.serial_thread.error_occurred.connect(self.show_error_message)
        self.serial_thread.start()
        # 검출된 객체 정보 저장 변수
        self.detection_data = []
        # 객체 검출 스레드 생성 및 시그널 연결
        self.detection_thread = DetectionThread()
        self.detection_thread.image_update.connect(self.update_image)
        self.detection_thread.detection_data_update.connect(self.update_detection_data)
        self.detection_thread.start()

        self.last_data_append_time = time.time()
        # Updating interval time
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)

        # PYQT SETUP
        self.systemstate = 1
        # 초기 아이콘 상태 설정
        self.is_toggle_on = False
        # 각 버튼의 초기 상태 설정
        self.is_fan_on = False
        self.is_fan2_on = False
        self.is_window1_on = False
        self.is_window2_on = False
        self.is_light_on = False
        # 각 버튼의 아이콘 초기 설정
        self.on_off_fan.setIcon(QIcon(":/off.png"))
        self.on_off_fan2.setIcon(QIcon(":/off.png"))
        self.on_off_window.setIcon(QIcon(":/off.png"))
        self.on_off_window2.setIcon(QIcon(":/off.png"))
        self.on_off_light.setIcon(QIcon(":/off.png"))

        # 스타일시트를 사용하여 배경을 투명하게 설정
        self.leftMenuSubContainer.setStyleSheet("background-color: transparent;")

        self.user_table = UserTable()

        # Water Tank Level
        self.pbar_waterlevel.valueChanged.connect(self.update_waterlevel_status)
        self.pbar_nutwaterlevel.valueChanged.connect(self.update_nutwaterlevel_status)
        self.update_waterlevel_status()
        self.update_nutwaterlevel_status()
        # Button Pressed
        self.loadBtn.clicked.connect(self.load_data)
        self.addBtn.clicked.connect(self.add_user)
        self.updateBtn.clicked.connect(self.update_user)
        self.deleteBtn.clicked.connect(self.delete_user)
        self.tableWidget.cellClicked.connect(self.load_selected_user)
        # tableWidget 설정 및 헤더 너비 확장 모드 적용
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["아이디", "패스워드"])  # 수정
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 헤더 너비 확장
        # 메뉴 초기 상태 설정 (확장된 상태)
        self.menuExpanded = True
        self.leftMenuSubContainer.setFixedWidth(150)
        # 헤더 스타일 적용 ###수정 ###
        header = self.tableWidget.horizontalHeader()
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        # 버튼 이름과 텍스트를 저장해두는 딕셔너리
        self.buttonTexts = {
            "DashboardBtn": "대시보드",
            "LogoutBtn": "로그아웃",
            "SettingsBtn": "관리자"
        }
        # 로그인 버튼 클릭 이벤트 연결
        self.pushButton_login.clicked.connect(self.login)
        # 엔터 키 누르면 로그인 버튼 클릭
        self.lineEdit_password.returnPressed.connect(self.pushButton_login.click)
        # 로그아웃 버튼 클릭 이벤트 연결
        self.LogoutBtn.clicked.connect(self.logout)
        # 버튼 클릭 시 메뉴를 확장/축소하는 이벤트 연결
        self.menuBtn.clicked.connect(self.toggleMenu)
        # 버튼 클릭 시 페이지 전환 및 강조 효과 적용
        self.DashboardBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.LoginBtn.clicked.connect(lambda: self.changePage(1, self.LoginBtn))
        self.LogoutBtn.clicked.connect(lambda: self.changePage(1, self.LoginBtn))
        self.SettingsBtn.clicked.connect(lambda: self.changePage(2, self.SettingsBtn))
        # shutdown_btn 클릭 이벤트 연결
        self.shutdown_btn.clicked.connect(self.confirm_shutdown)
        # 초기 화면을 로그인 페이지로 설정
        self.stackedWidget.setCurrentIndex(1)
        self.changePage(1, self.LoginBtn)
        self.currentActiveButton = None
        # 초기 버튼 비활성화 및 스타일 설정
        self.DashboardBtn.setEnabled(False)
        self.SettingsBtn.setEnabled(False)
        self.LogoutBtn.setEnabled(False)
        style_disabled = """
            QPushButton:disabled {
                color: gray;
            }
        """
        self.DashboardBtn.setStyleSheet(style_disabled)
        self.SettingsBtn.setStyleSheet(style_disabled)
        self.LogoutBtn.setStyleSheet(style_disabled)
        # 다이얼 설정
        self.dial_2.setMinimum(0)
        self.dial_2.setMaximum(7)
        self.dial_2.valueChanged.connect(self.on_dial_change)
        # 다이얼 슬라이더 조작 시 페이지 전환 방지
        self.dial_2.sliderPressed.connect(lambda: None)
        self.set_dial_2_color("gray")  # 초기 색상 설정

        # Arduino connection status
        self.le_connection_status.setText("Connecting to Arduino...")

        # Data read for display
        self.temperature = 0
        self.humidity = 0
        self.soilmoisture = 0
        self.waterlevel = 0
        self.nutritionwaterlevel = 0
        self.mapped_waterlevel = 0
        self.mapped_nutritionwaterlevel = 0
        self.security_state = False
        self.normal_count = 0
        self.abnormal_count = 0

        self.temperature_str = "0"
        self.humidity_str = "0"
        self.waterlevel_str = "0"
        self.nutritionwaterlevel_str = "0"
        self.soilmoisture_str = "0"
        # Graph setup
        self.x = np.arange(10)  # x range 20으로 고정
        self.temperature_data = np.zeros(10)  # array로 저장
        self.humidity_data = np.zeros(10)
        self.soilmoisture_data = np.zeros(10)

        self.humidity_canvas = pg.GraphicsLayoutWidget()
        self.wdg_humidity.setLayout(QVBoxLayout())
        self.wdg_humidity.layout().addWidget(self.humidity_canvas)
        self.HumidityPlot = self.humidity_canvas.addPlot()
        self.HumidityPlot.setXRange(0, 10)
        self.HumidityPlot.setYRange(0, 100)
        self.HumidityPlotLine = self.HumidityPlot.plot(pen='b')  # 그래프 라인만 따로 업데이트

        self.temperature_canvas = pg.GraphicsLayoutWidget()
        self.wdg_temperature.setLayout(QVBoxLayout())
        self.wdg_temperature.layout().addWidget(self.temperature_canvas)
        self.temperaturePlot = self.temperature_canvas.addPlot()
        self.temperaturePlot.setXRange(0, 10)
        self.temperaturePlot.setYRange(0, 30)
        self.temperaturePlotLine = self.temperaturePlot.plot(pen='g')  # 그래프 라인만 따로 업데이트

        self.soilmoisture_canvas = pg.GraphicsLayoutWidget()
        self.wdg_soilmoisture.setLayout(QVBoxLayout())
        self.wdg_soilmoisture.layout().addWidget(self.soilmoisture_canvas)
        self.soilmoisturePlot = self.soilmoisture_canvas.addPlot()
        self.soilmoisturePlot.setXRange(0, 10)
        self.soilmoisturePlot.setYRange(0, 100)
        self.soilmoisturePlotLine = self.soilmoisturePlot.plot(pen='y')  # 그래프 라인만 따로 업데이트

        self.graph24_canvas = pg.GraphicsLayoutWidget()
        self.wdg_graph24.setLayout(QVBoxLayout())
        self.wdg_graph24.layout().addWidget(self.graph24_canvas)
        self.plot_graph24()
        # get available dates list in DB
        self.date_list = self.get_date_list()
        # push list to combo box
        self.comboBox.addItems(self.date_list)
        self.comboBox.currentIndexChanged.connect(self.combo_value)

        # 물 넣어주는 함수
        self.pushButton_17.clicked.connect(self.water_push)
        self.pushButton_18.clicked.connect(self.nutri_push)
        # Read dial value
        self.dial_2.valueChanged.connect(self.dial_value_status)
        self.dial_value = self.dial_2.value()

    # ----------------------------------- FUNCTIONS -----------------------------------
    def water_push(self):
        data_str_for_main = str("9")
        self.serial_thread.arduinoMainData.write(data_str_for_main.encode())

    def nutri_push(self):
        data_str_for_main = str("10")
        self.serial_thread.arduinoMainData.write(data_str_for_main.encode())

    # DeepLearning
    def closeEvent(self, event):
        # 스레드 정지 및 자원 해제
        self.detection_thread.stop()
        self.serial_thread.stop()
        event.accept()

    def update_image(self, qt_image):
        # 이미지 레이블에 업데이트
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def update_detection_data(self, detection_array):
        # 검출된 객체 정보를 업데이트
        self.detection_data = detection_array

    def find_normal_and_abnormal(self):
        normal_count_ = 0
        abnormal_count_ = 0
        for dictionary in self.detection_data:
            if dictionary["label"] == "normal":
                normal_count_ += 1
            else:
                abnormal_count_ += 1
        self.normal_count = normal_count_
        self.abnormal_count = abnormal_count_

    def send_data_to_arduinoSubData(self, data):  # reset 버튼에서 호출
        data_str = str(data) + "\n"  # 데이터 뒤에 줄바꿈 추가 (아두이노에서 한 줄 단위로 읽을 수 있도록)
        self.serial_thread.arduinoSubData.write(data_str.encode())  # 데이터를 인코딩하여 전송

    def system_off(self):
        data_str_for_main = str("1000") + "\n"
        self.serial_thread.arduinoMainData.write(data_str_for_main.encode())
        data_str_for_sub = str("0")
        self.serial_thread.arduinoSubData.write(data_str_for_sub.encode())

    def system_on(self):
        print("system on")
        data_str_for_main = str("2000")
        self.serial_thread.arduinoMainData.write(data_str_for_main.encode())
        data_str_for_sub = str("2")
        self.serial_thread.arduinoSubData.write(data_str_for_sub.encode())

    # 시그널을 통한 메인 데이터 처리
    def handle_main_data(self, data):
        print("data", data)
        try:
            if "Temperature:" in data and "Humidity:" in data and 'Water Level:' in data and 'Nutrition Water Level:' in data and 'Soil Moisture:' in data:
                self.temperature_str = data.split("Temperature:")[1].split(",")[0].strip()
                self.humidity_str = data.split("Humidity:")[1].split(",")[0].strip()
                self.waterlevel_str = data.split("Water Level:")[1].split(",")[0].strip()
                self.nutritionwaterlevel_str = data.split("Nutrition Water Level:")[1].split(",")[0].strip()
                self.soilmoisture_str = data.split("Soil Moisture:")[1].split(",")[0].strip()

                # 값 변환
                self.temperature = int(self.temperature_str)
                self.humidity = int(self.humidity_str)
                self.soilmoisture = int(self.soilmoisture_str)
                self.waterlevel = int(self.waterlevel_str)
                self.mapped_waterlevel = int(((self.waterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
                self.nutritionwaterlevel = int(self.nutritionwaterlevel_str)
                self.mapped_nutritionwaterlevel = int(((self.nutritionwaterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
        except (ValueError, IndexError):
            print("Data format error:", data)

    # 시그널을 통한 서브 데이터 처리
    def handle_sub_data(self, data2):
        print("data2: ", data2)
        try:
            if "Security:" in data2:
                state = data2[-1:]
                current_time = time.time()
                if state == "2":
                    self.security_state = True
                    self.state1_start_time = None
                elif state == "1":
                    self.security_state = False
                    if self.state1_start_time is None:
                        self.state1_start_time = current_time
                    elif current_time - self.state1_start_time > 10:
                        self.system_off()  # 10초 이상 지속되면 도난으로 판단하고 system off 실행
                else:
                    self.security_state = False
                    self.state1_start_time = None
        except (ValueError, IndexError):
            print("data error:", data2)

    def update_plot(self):
        self.find_normal_and_abnormal()
        # Update plot data (array)
        self.temperature_data = np.roll(self.temperature_data, -1)
        self.temperature_data[-1] = self.temperature
        self.humidity_data = np.roll(self.humidity_data, -1)
        self.humidity_data[-1] = self.humidity
        self.soilmoisture_data = np.roll(self.soilmoisture_data, -1)
        self.soilmoisture_data[-1] = self.soilmoisture
        # Update displayed value in GUI
        self.le_temperature.setText(f"{self.temperature_str} °C")
        self.le_humidity.setText(f"{self.humidity_str} %")
        self.le_waterlevel.setText(f"{self.mapped_waterlevel} %")
        self.le_nutwaterlevel.setText(f"{self.mapped_nutritionwaterlevel} %")
        self.le_normal_count.setText(f"Normal Seed: {self.normal_count}")
        self.le_abnormal_count.setText(f"Abnormal Seed: {self.abnormal_count} ")
        self.le_soilmoisture.setText(f"{self.soilmoisture} %")
        self.pbar_waterlevel.setValue(self.mapped_waterlevel)
        self.pbar_nutwaterlevel.setValue(self.mapped_nutritionwaterlevel)
        # Update displayed graph line in GUI
        self.temperaturePlotLine.setData(self.x, self.temperature_data)
        self.HumidityPlotLine.setData(self.x, self.humidity_data)
        self.soilmoisturePlotLine.setData(self.x, self.soilmoisture_data)
        # Insert data into the database every 1 second
        farm_table = SmartFarmTable()
        current_time = time.time()
        if current_time - self.last_data_append_time >= 1.0:
            farm_table = SmartFarmTable()
            farm_table.append(self.mapped_waterlevel, self.mapped_nutritionwaterlevel,
                              self.soilmoisture, self.humidity, self.temperature,
                              self.security_state, self.normal_count, self.abnormal_count)
            self.last_data_append_time = current_time

    # Log in & GUI Functions
    def show_error_message(self, title, message):
        # Qt 알림창을 통해 에러 메시지를 표시합니다.
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    # GUI function
    def toggle_device(self, device):
        """각 장치의 on/off 상태를 전환합니다."""
        if device == "fan":
            self.is_fan_on = not self.is_fan_on
            self.on_off_fan.setIcon(QIcon(":/on.png") if self.is_fan_on else QIcon(":/off.png"))
        elif device == "fan2":
            self.is_fan2_on = not self.is_fan2_on
            self.on_off_fan2.setIcon(QIcon(":/on.png") if self.is_fan2_on else QIcon(":/off.png"))
        elif device == "window1":
            self.is_window1_on = not self.is_window1_on
            self.on_off_window.setIcon(QIcon(":/on.png") if self.is_window1_on else QIcon(":/off.png"))
        elif device == "window2":
            self.is_window2_on = not self.is_window2_on
            self.on_off_window2.setIcon(QIcon(":/on.png") if self.is_window2_on else QIcon(":/off.png"))
            self.is_light_on = not self.is_light_on
            self.on_off_light.setIcon(QIcon(":/on.png") if self.is_light_on else QIcon(":/off.png"))

    def toggleMenu(self):
        target_width = 50 if self.menuExpanded else 150

        if self.menuExpanded:
            for btn_name in self.buttonTexts:
                getattr(self, btn_name).setText("")  # 텍스트 숨기기
        else:
            for btn_name, text in self.buttonTexts.items():
                getattr(self, btn_name).setText(text)  # 텍스트 복원

        self.animation = QPropertyAnimation(self.leftMenuSubContainer, b"minimumWidth")
        self.animation.setDuration(500)
        self.animation.setStartValue(self.leftMenuSubContainer.width())
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
        self.animation.start()

        self.menuExpanded = not self.menuExpanded

    def changePage(self, index, active_button, buttons=None):
        if buttons is None:
            buttons = [self.DashboardBtn, self.SettingsBtn, self.LogoutBtn, self.LoginBtn]
        self.stackedWidget.setCurrentIndex(index)

        default_style = """
            QPushButton {
                background-color: #588460;
                color: black;
                border: none;
                text-align: left;
                padding: 5px 10px;
                border-radius: 5px;
            }

            QPushButton:disabled {
                color: gray;
            }

            QPushButton#LoginBtn {
                background-color: transparent;  /* 버튼 배경색: 투명 */
            }

            QPushButton:focus {
                outline: none;  /* 포커스 시 테두리 제거 */
            }
        """

        active_style = """
            QPushButton {
                background-color: #A9D6B2;
                color: black;
                border: none;
                text-align: left;
                padding: 5px 10px;
                border-radius: 5px;
            }

            QPushButton:focus {
                outline: none;  /* 포커스 시 테두리 제거 */
            }
        """
        # 버튼 스타일 업데이트
        for button in buttons:
            if button == active_button:
                button.setStyleSheet(active_style)
            else:
                button.setStyleSheet(default_style)

        # 현재 활성화된 버튼 업데이트
        self.currentActiveButton = active_button

    def login(self):
        user_id = self.lineEdit_id.text()
        user_pw = self.lineEdit_password.text()

        msg = QMessageBox(self)
        msg.setStyleSheet("""QLabel { color : black; } QPushButton {color : black;}""")  # 텍스트 색상 설정 #수정함

        if self.user_table.login(user_id, user_pw):
            msg.setWindowTitle("로그인 성공")
            msg.setText(f"{user_id}님 환영합니다!")
            msg.exec_()
            # 버튼 활성화
            self.DashboardBtn.setEnabled(True)
            self.SettingsBtn.setEnabled(True)
            self.LogoutBtn.setEnabled(True)
            # LoginBtn 비활성화  #수정
            self.LoginBtn.setEnabled(False)  # 수정

            # 대시보드 페이지로 이동 및 스타일 업데이트
            self.changePage(0, self.DashboardBtn, [self.DashboardBtn, self.SettingsBtn, self.LogoutBtn, self.LoginBtn])

            # LoginBtn을 투명하게 설정
            style_transparent = """
                QPushButton {
                    background-color: transparent;
                    color: black;
                    border: none;
                    text-align: left;
                    padding: 5px 10px;
                }
            """
            self.LoginBtn.setStyleSheet(style_transparent)
            self.SettingsBtn.setStyleSheet(style_transparent)
            self.LogoutBtn.setStyleSheet(style_transparent)

            # 로그인 되면 조명 자동으로 켜져 있음
            self.on_off_light.setIcon(QIcon(":/on.png"))
        else:
            msg.setWindowTitle("로그인 실패")
            msg.setText("아이디 또는 비밀번호가 잘못되었습니다.")
            msg.exec_()

    def load_data(self):
        data = self.user_table.load_data()
        self.tableWidget.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            self.tableWidget.setItem(row_idx, 0, QTableWidgetItem(row_data[0]))
            self.tableWidget.setItem(row_idx, 1, QTableWidgetItem(row_data[1]))

    def add_user(self):
        user_id = self.id_input.text()
        user_pw = self.pw_input.text()

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black;} QPushButton { color: black;}")  # 텍스트 색상을 검은색으로 설정

        if self.user_table.append_user(user_id, user_pw):
            msg.setWindowTitle("추가 성공")
            msg.setText(f"{user_id}가 추가되었습니다.")
            msg.exec_()
            self.load_data()  # 새로고침
            self.id_input.clear()
            self.pw_input.clear()
        else:
            msg.setWindowTitle("추가 실패")
            msg.setText("중복된 ID가 있습니다.")
            msg.exec_()
            self.id_input.clear()
            self.pw_input.clear()

    def update_user(self):
        user_id = self.id_input.text()
        user_pw = self.pw_input.text()

        self.user_table.update_user(user_id, user_pw)

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black; } QPushButton { color: black; }")  # 텍스트 색상을 검은색으로 설정
        msg.setWindowTitle("수정 성공")
        msg.setText(f"{user_id}의 비밀번호가 수정되었습니다.")
        msg.exec_()

        self.load_data()  # 새로고침
        self.id_input.clear()
        self.pw_input.clear()

    def delete_user(self):
        user_id = self.id_input.text()

        self.user_table.delete_user(user_id)

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black; } QPushButton { color: black; }")  # 텍스트 색상을 검은색으로 설정
        msg.setWindowTitle("삭제 성공")
        msg.setText(f"{user_id}가 삭제되었습니다.")
        msg.exec_()

        self.load_data()  # 새로고침
        self.id_input.clear()
        self.pw_input.clear()

    def load_selected_user(self, row, column):
        selected_id = self.tableWidget.item(row, 0).text()
        selected_pw = self.tableWidget.item(row, 1).text()
        self.id_input.setText(selected_id)
        self.pw_input.setText(selected_pw)

    def on_dial_change(self, value):
        """다이얼 값에 따라 아이콘 상태를 업데이트합니다."""
        # 기본적으로 모든 아이콘 OFF로 설정
        self.on_off_light.setIcon(QIcon(":/off.png"))
        self.on_off_fan.setIcon(QIcon(":/off.png"))
        self.on_off_fan2.setIcon(QIcon(":/off.png"))
        self.on_off_window.setIcon(QIcon(":/off.png"))
        self.on_off_window2.setIcon(QIcon(":/off.png"))
        self.on_off_heating.setIcon(QIcon(":/off.png"))
        # 조건에 따라 필요한 아이콘만 ON으로 설정
        if value == 0:
            self.on_off_light.setIcon(QIcon(":/on.png"))  # 조명만 켜짐
            self.set_dial_2_color("gray")
        elif value in {1, 2, 3}:
            self.on_off_light.setIcon(QIcon(":/on.png"))  # 조명 켜짐
            self.on_off_fan.setIcon(QIcon(":/on.png"))
            self.on_off_fan2.setIcon(QIcon(":/on.png"))
            self.on_off_window.setIcon(QIcon(":/on.png"))
            self.on_off_window2.setIcon(QIcon(":/on.png"))  # 팬과 창문 켜짐
            self.set_dial_2_color("blue")
        elif value in {4, 5, 6}:
            self.on_off_light.setIcon(QIcon(":/on.png"))
            self.on_off_heating.setIcon(QIcon(":/on.png"))  # 난방 모드
            self.set_dial_2_color("red")
        elif value == 7:
            # AUTO 모드: 모든 장치 ON
            self.on_off_light.setIcon(QIcon(":/on.png"))
            self.on_off_fan.setIcon(QIcon(":/on.png"))
            self.on_off_fan2.setIcon(QIcon(":/on.png"))
            self.on_off_window.setIcon(QIcon(":/off.png"))
            self.on_off_window2.setIcon(QIcon(":/off.png"))
            self.on_off_heating.setIcon(QIcon(":/off.png"))
            self.set_dial_2_color("yellow")

    def update_waterlevel_status(self):
        water_level = self.pbar_waterlevel.value()
        if water_level <= 50:
            # waterlevel_color 색상 빨강색으로 변경
            self.waterlevel_color.setStyleSheet("background-color: red; border-radius: 15px;")
            # waterlevel_green_label 텍스트 "물 채워주세요"로 변경
            self.waterlevel_text_label.setText("물 채워주세요")
            self.waterlevel_text_label.setStyleSheet("color: red;")
        else:
            # waterlevel_color 색상 파랑색으로 변경
            self.waterlevel_color.setStyleSheet("background-color: blue; border-radius: 15px;")
            # waterlevel_green_label 텍스트 "수위 정상"으로 변경
            self.waterlevel_text_label.setText(" 수위 정상")
            self.waterlevel_text_label.setStyleSheet("color: blue;")

    def update_nutwaterlevel_status(self):
        nutwater_level = self.pbar_nutwaterlevel.value()
        if nutwater_level <= 50:
            # nutwaterlevel_color 색상 빨강색으로 변경
            self.nutwaterlevel_color.setStyleSheet("background-color: red; border-radius: 15px;")
            # nutwaterlevel_text_label 텍스트 "배양액 채워주세요"로 변경
            self.nutwaterlevel_text_label.setText("  배양액 채워주세요")
            self.nutwaterlevel_text_label.setStyleSheet("color: red;")
        else:
            # nutwaterlevel_color 색상 파랑색으로 변경
            self.nutwaterlevel_color.setStyleSheet("background-color: blue; border-radius: 15px;")
            # waterlevel_text_label_2 텍스트 "수위 정상"으로 변경
            self.nutwaterlevel_text_label.setText("수위 정상")
            self.nutwaterlevel_text_label.setStyleSheet("color: blue;")

    def confirm_shutdown(self):
        # 현재 버튼 상태 확인
        if self.shutdown_btn.text() == "작동시작":
            self.system_on()
            # 이미 '작동시작' 상태인 경우
            self.shutdown_btn.setText("시스템 종료")
            self.shutdown_btn.setStyleSheet(""" 
                QPushButton {
                    background-color: rgb(237, 51, 59); /* 원래 버튼 색상 */
                    border: 2px solid #387038; /* 테두리 색 */
                    border-radius: 10px; /* 둥근 모서리 */
                    padding: 5px 15px;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:pressed {
                    background-color: #8FBD99; /* 눌렀을 때 배경색 */
                    padding-top: 6px;
                    padding-left: 6px;
                }
                QPushButton:focus {
                    outline: none;  /* 포커스 시 테두리 제거 */
                }
            """)

            return  # QMessageBox를 건너뜀
        # QMessageBox 객체 생성
        msg = QMessageBox(self)
        msg.setWindowTitle("시스템 종료")
        msg.setText("정말로 종료하겠습니까?")
        msg.setIcon(QMessageBox.Warning)
        # '예' 버튼 생성 및 추가
        yes_button = QPushButton("예")
        yes_button.clicked.connect(self.system_off)
        msg.addButton(yes_button, QMessageBox.YesRole)
        # '아니요' 버튼 생성 및 추가
        no_button = QPushButton("아니요")
        msg.addButton(no_button, QMessageBox.NoRole)
        # 버튼 스타일 텍스트 색상 설정
        yes_button.setStyleSheet("""
          QPushButton {
                color: black;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        yes_button.setMinimumWidth(100)  # 버튼 최소 너비 설정
        yes_button.setMinimumHeight(30)  # 버튼 최소 높이 설정
        no_button.setStyleSheet("""
            QPushButton {
                color: black;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
                # 스타일시트 설정
        msg.setStyleSheet("""
            QMessageBox QLabel {
                color: black;  /* 텍스트 색상 검은색으로 설정 */
            }
        """)
        no_button.setMinimumWidth(100)  # 버튼 최소 너비 설정
        no_button.setMinimumHeight(30)  # 버튼 최소 높이 설정
        # 메시지 박스 실행 및 선택 확인
        msg.exec_()
        # '예' 버튼이 클릭된 경우
        if msg.clickedButton() == yes_button:
            self.shutdown_btn.setText("작동시작")
            self.shutdown_btn.setStyleSheet(""" 
                QPushButton {
                    background-color: lightgreen; /* 연두색 배경 */
                    border: 2px solid #387038; /* 테두리 색 */
                    border-radius: 10px; /* 둥근 모서리 */
                    padding: 5px 15px;
                    color: black;
                    font-weight: bold;
                }
                QPushButton:pressed {
                    background-color: #8FBD99; /* 눌렀을 때 배경색 */
                    padding-top: 6px;
                    padding-left: 6px;
                }
                QPushButton:focus {
                    outline: none;  /* 포커스 시 테두리 제거 */
                }                                            
            """)

    def set_dial_2_color(self, color):
        """다이얼에 고정 배경색을 적용합니다."""
        color_styles = {
            "gray": "#E0E0E0",
            "blue": "#4682b4",
            "red": "#8b0000",
            "yellow": "#ffd700"
        }

        selected_color = color_styles.get(color, "#808080")  # 색상이 없을 경우 기본 회색으로 설정

        # 다이얼에 색상 스타일을 직접 적용
        self.dial_2.setStyleSheet(f"""
            QDial {{
                background-color: {selected_color};
                border-radius: {self.dial_2.width() // 2}px;
            }}
        """)

    def dial_value_status(self, value):
        self.dial_value = value
        print(f"Dial value: {self.dial_value}")
        self.serial_thread.arduinoMainData.write(str(self.dial_value).encode())

    def logout(self):
        # 버튼 비활성화
        self.DashboardBtn.setEnabled(False)
        self.SettingsBtn.setEnabled(False)
        self.LogoutBtn.setEnabled(False)
        self.LoginBtn.setEnabled(True)
        style_disabled = """
            QPushButton:disabled {
                color: gray;
                background-color: transparent;  /* 비활성화 시 회색 배경 */
            }

            QPushButton:focus {
                outline: none;  /* 포커스 시 테두리 제거 */
            }            
        """
        self.DashboardBtn.setStyleSheet(style_disabled)
        self.SettingsBtn.setStyleSheet(style_disabled)
        self.LogoutBtn.setStyleSheet(style_disabled)
        # 입력 필드 초기화
        self.lineEdit_id.clear()
        self.lineEdit_password.clear()
        self.id_input.clear()
        self.pw_input.clear()
        # 메시지 출력 (선택 사항)
        msg = QMessageBox(self)
        msg.setWindowTitle("로그아웃")
        msg.setText("로그아웃되었습니다.")
        msg.setStyleSheet("QLabel { color: black; } QPushButton { color: black; }")
        msg.exec_()

    def plot_graph24(self):
            self.conn = pymysql.connect(host='localhost', user='root', password= "whdgh29k05" ,charset='utf8')
            self.cursor = self.conn.cursor()
            self.cursor.execute("USE smart_farm ;")
            self.cursor.execute("SET @row_number = 0;")
            interval_query = """
                SELECT *
                FROM (
                    SELECT *, (@row_number := @row_number + 1) AS rn
                    FROM SMART_FARM
                    ORDER BY Time DESC
                ) AS NumberedRows
                WHERE MOD(rn, 1800) = 0
                ORDER BY Time DESC
                LIMIT 24;
            """
            self.cursor.execute(interval_query)
            interval_rows = self.cursor.fetchall()
            # 컬럼 이름 가져오기
            column_names = [desc[0] for desc in self.cursor.description]
            df = pd.DataFrame(interval_rows, columns=column_names)
            df['Time'] = pd.to_datetime(df['Time'])
            self.cursor.close()
            self.conn.close()
            x = np.arange(len(df))
            y_water = df['Water_Level'].values
            y_nutrient = df['Nutrient_Level'].values
            print("Water Level:", y_water)
            print("Nutrient Level:", y_nutrient)
            self.graph24_plot = self.graph24_canvas.addPlot(title="Water and Nutrient Levels Over Time")
            self.graph24_plot.clear()
            water_graph = self.graph24_plot.plot(x, y_water, pen='skyblue', name='Water Level')
            nutrient_graph = self.graph24_plot.plot(x, y_nutrient, pen='green', name='Nutrient Level')
            water_graph = self.graph24_plot.plot(x, y_water, pen='skyblue', name='Water Level')
            nutrient_graph = self.graph24_plot.plot(x, y_nutrient, pen='green', name='Nutrient Level')
            self.legend = self.graph24_plot.addLegend()
            self.legend.addItem(water_graph, 'Water Level')
            self.legend.addItem(nutrient_graph, 'Nutrient Level')
            self.graph24_plot.setLabel("left", "Level (%)")
            self.graph24_plot.setLabel("bottom", "Time")
            self.graph24_plot.setTitle("Water and Nutrient Levels Over 24 Hours")
            self.graph24_canvas.update()

    def plot_graph_history(self):
        date = self.combo_value()
        self.conn = pymysql.connect(host='localhost', user='root', password= "whdgh29k05" ,charset='utf8')
        self.cursor = self.conn.cursor()
        self.cursor.execute("USE smart_farm ;")
        self.cursor.execute("SET @row_number = 0;")
        interval_query = f"""
            SELECT *
            FROM (
                SELECT *, (@row_number := @row_number + 1) AS rn
                FROM SMART_FARM
                WHERE DATE(Time) = '{date}'
                ORDER BY Time DESC
            ) AS NumberedRows
            WHERE MOD(rn, 1800) = 0
            ORDER BY Time DESC
            LIMIT 24;
            """
        self.cursor.execute(interval_query)
        interval_rows = self.cursor.fetchall()
        # 컬럼 이름 가져오기
        column_names = [desc[0] for desc in self.cursor.description]
        df = pd.DataFrame(interval_rows, columns=column_names)
        df['Time'] = pd.to_datetime(df['Time'])
        self.cursor.close()
        self.conn.close()
        x = np.arange(len(df))
        y_water = df['Water_Level'].values
        y_nutrient = df['Nutrient_Level'].values
        print("Water Level:", y_water)
        print("Nutrient Level:", y_nutrient)
        self.graph24_plot = self.graph24_canvas.addPlot(title="Water and Nutrient Levels Over Time")
        self.graph24_plot.clear()
        water_graph = self.graph24_plot.plot(x, y_water, pen='skyblue', name='Water Level')
        nutrient_graph = self.graph24_plot.plot(x, y_nutrient, pen='green', name='Nutrient Level')
        water_graph = self.graph24_plot.plot(x, y_water, pen='skyblue', name='Water Level')
        nutrient_graph = self.graph24_plot.plot(x, y_nutrient, pen='green', name='Nutrient Level')
        # i am trying to update the whole grapd whenever combo
        self.legend = self.graph24_plot.addLegend()
        self.legend.addItem(water_graph, 'Water Level')
        self.legend.addItem(nutrient_graph, 'Nutrient Level')
        self.graph24_plot.setLabel("left", "Level (%)")
        self.graph24_plot.setLabel("bottom", "Time")
        self.graph24_plot.setTitle("Water and Nutrient Levels Over 24 Hours")

    def get_date_list(self):
        self.conn = pymysql.connect(host='localhost', user='root', password= "whdgh29k05" ,charset='utf8')
        self.cursor = self.conn.cursor()
        self.cursor.execute("USE smart_farm ;")
        query = """
        SELECT DISTINCT DATE(Time) AS unique_date
        FROM SMART_FARM
        ORDER BY unique_date DESC;
        """
        self.cursor.execute(query)
        dates = self.cursor.fetchall()
        date_strings = [str(date[0]) for date in dates]
        return date_strings

    def combo_value(self):
        selected_date = self.comboBox.currentText()
        print(selected_date)
        return selected_date


if __name__ == '__main__':
    App = QApplication(sys.argv)
    myWindow = SunnyMainWindow()
    myWindow.show()
    sys.exit(App.exec())
