import numpy as np
import pandas as pd
import cv2
import sys
import pymysql
import sys
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




# Main Window
class SunnyMainWindow(QMainWindow, form_class):  # QWidget vs QMainWindow
    def __init__(self):
        super(SunnyMainWindow, self).__init__()
        self.setupUi(self)

        # 시리얼 포트를 타임아웃과 함께 초기화
        self.arduinoMainData = serial.Serial(main_usd_port, 9600, timeout=0.1)
        self.arduinoSubData = serial.Serial(sub_usd_port, 9600, timeout=0.1)

        # 시리얼 읽기 스레드 시작
        self.serial_thread = threading.Thread(target=self.read_serial_data)
        self.serial_thread.daemon = True
        self.serial_thread.start()

        # 검출된 객체 정보 저장 변수
        self.detection_data = []
        # 객체 검출 스레드 생성 및 시그널 연결
        self.detection_thread = DetectionThread()
        self.detection_thread.image_update.connect(self.update_image)
        self.detection_thread.detection_data_update.connect(self.update_detection_data)
        self.detection_thread.start()


        self.last_data_append_time = time.time()

        # 업데이트 주기
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)  # 100 밀리초마다 업데이트


        # SET ATTRIBUTE PROPERTY -------------------------------------------------------------------------

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

        # UserTable 인스턴스 생성
        self.user_table = UserTable()

        # 버튼 이벤트 연결
        self.loadBtn.clicked.connect(self.load_data)
        self.addBtn.clicked.connect(self.add_user)
        self.updateBtn.clicked.connect(self.update_user)
        self.deleteBtn.clicked.connect(self.delete_user)
        self.tableWidget.cellClicked.connect(self.load_selected_user)

        # tableWidget 설정 및 헤더 너비 확장 모드 적용
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["ID", "Password"])
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 헤더 너비 확장

        # 메뉴 초기 상태 설정 (확장된 상태)
        self.menuExpanded = True
        self.leftMenuSubContainer.setFixedWidth(150)

        # 버튼 이름과 텍스트를 저장해두는 딕셔너리
        self.buttonTexts = {
            "DashboardBtn": "대시보드",
            "LogoutBtn": "로그아웃",
            "SettingsBtn": "관리자"
        }

        # 로그인 버튼 클릭 이벤트 연결
        self.pushButton_login.clicked.connect(self.login)

        # 버튼 클릭 시 메뉴를 확장/축소하는 이벤트 연결
        self.menuBtn.clicked.connect(self.toggleMenu)

        # 버튼 클릭 시 페이지 전환 및 강조 효과 적용
        self.DashboardBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.LoginBtn.clicked.connect(lambda: self.changePage(1, self.LoginBtn))
        self.LogoutBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.SettingsBtn.clicked.connect(lambda: self.changePage(2, self.SettingsBtn))

        # 초기 화면을 대시보드 페이지로 설정
        self.stackedWidget.setCurrentIndex(0)
        self.changePage(1, self.DashboardBtn)

        # 다이얼 설정
        self.dial_2.setMinimum(0)
        self.dial_2.setMaximum(7)
        self.dial_2.valueChanged.connect(self.on_dial_change)
        # 다이얼 슬라이더 조작 시 페이지 전환 방지
        self.dial_2.sliderPressed.connect(lambda: None)
        self.set_dial_2_color("gray")  # 초기 색상 설정


        # Arduino connection status

        self.le_connection_status.setText("Connecting to Arduino...")
        # 그래프가 들어갈 attribute 생성
        self.humidity_canvas = pg.GraphicsLayoutWidget()
        # PyQt에서 만든 attribute에 삽입
        self.wdg_humidity.setLayout(QVBoxLayout())
        self.wdg_humidity.layout().addWidget(self.humidity_canvas)

        self.temperature_canvas = pg.GraphicsLayoutWidget()
        self.wdg_temperature.setLayout(QVBoxLayout())
        self.wdg_temperature.layout().addWidget(self.temperature_canvas)

        self.HumidityPlot = self.humidity_canvas.addPlot()
        self.HumidityPlot.setXRange(0, 20)
        self.HumidityPlot.setYRange(0, 100)
        self.HumidityPlotLine = self.HumidityPlot.plot(pen='b')  # 그래프 라인만 따로 업데이트

        self.temperaturePlot = self.temperature_canvas.addPlot()
        self.temperaturePlot.setXRange(0, 20)
        self.temperaturePlot.setYRange(0, 30)
        self.temperaturePlotLine = self.temperaturePlot.plot(pen='g')  # 그래프 라인만 따로 업데이트

        self.x = np.arange(20)  # x range 20으로 고정
        self.temperature_data = np.zeros(20)  # array로 저장
        self.humidity_data = np.zeros(20)

        self.temperature_str = "0"
        self.humidity_str = "0"
        self.waterlevel_str = "0"
        self.nutritionwaterlevel_str = "0"

        self.temperature = 0
        self.humidity = 0
        self.soilhumidity = 0
        self.waterlevel = 0
        self.nutritionwaterlevel = 0
        self.mapped_waterlevel = 0
        self.mapped_nutritionwaterlevel = 0
        self.security_state = False
        self.normal_count = 0
        self.abnormal_count = 0

        

        # GUI Read
        # 그냥 print 하는 함수 사용
        self.dial_2.valueChanged.connect(self.dial_value_status)

        self.dial_value = self.dial_2.value()
        serial.Serial(main_usd_port, 9600, timeout=1).write(str(self.dial_value).encode())

    # DeepLearning
    def closeEvent(self, event):
        # 스레드 정지 및 자원 해제
        self.detection_thread.stop()
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
        self.arduinoSubData.write(data_str.encode())  # 데이터를 인코딩하여 전송

    # 별도 스레드에서 시리얼 데이터 읽기
    def read_serial_data(self):
        last_received_time_main = time.time()
        last_received_time_sub = time.time()

        while True:
            current_time = time.time()


            # Arduino Sub 연결 상태 확인 및 데이터 읽기
            try:
                if not self.arduinoSubData.is_open:
                    self.arduinoSubData.open()

                data2 = self.arduinoSubData.readline().decode("utf-8").strip()

                if data2:
                    print("data2: ", data2)
                    last_received_time_sub = current_time  # 데이터 수신 시간 갱신

                    try:
                        if "Security:" in data2 :
                            #state = data2.split("Security:")[1].strip()
                            state =data2[-1:]
                            print("data2 split", state)
                            self.security_state = state == "2"
                    except (ValueError, IndexError):
                        print("data error:", data2)
                else:
                    # 빈 메시지가 5초 이상 지속되면 에러 메시지 출력
                    if current_time - last_received_time_sub > 5:
                        self.show_error_message("Arduino Sub 데이터 수신 오류", "5초 이상 데이터를 받지 못했습니다.")

            except SerialException:
                self.show_error_message("Arduino Sub 연결 끊어짐 오류", "Arduino Sub와의 연결이 끊어졌습니다.")
            except Exception as e:
                print(f"Unexpected error from Arduino Sub: {e}")




            # Arduino Main 연결 상태 확인 및 데이터 읽기
            try:
                if not self.arduinoMainData.is_open:
                    self.arduinoMainData.open()

                data = self.arduinoMainData.readline().decode('utf-8').strip()

                if data:
                    print("data", data)
                    last_received_time_main = current_time  # 데이터 수신 시간 갱신

                    try:
                        if "Temperature:" in data and "Humidity:" in data and 'Water Level:' in data and 'Nutrition Water Level:' in data:
                            self.temperature_str = data.split("Temperature:")[1].split(",")[0].strip()
                            self.humidity_str = data.split("Humidity:")[1].split(",")[0].strip()
                            self.waterlevel_str = data.split("Water Level:")[1].split(",")[0].strip()
                            self.nutritionwaterlevel_str = data.split("Nutrition Water Level:")[1].split(",")[0].strip()

                            # 값 변환
                            self.temperature = int(self.temperature_str)
                            self.humidity = int(self.humidity_str)
                            self.soilhumidity = int(self.humidity_str)
                            self.waterlevel = int(self.waterlevel_str)
                            self.mapped_waterlevel = int(((self.waterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
                            self.nutritionwaterlevel = int(self.nutritionwaterlevel_str)
                            self.mapped_nutritionwaterlevel = int(((self.nutritionwaterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
                    except (ValueError, IndexError):
                        print("Data format error:", data)
                else:
                    # 빈 메시지가 5초 이상 지속되면 에러 메시지 출력
                    if current_time - last_received_time_main > 5:
                        self.show_error_message("Arduino Main 데이터 수신 오류", "5초 이상 데이터를 받지 못했습니다.")

            except SerialException:
                self.show_error_message("Arduino Main 연결 끊어짐 오류", "Arduino Main과의 연결이 끊어졌습니다.")
            except Exception as e:
                print(f"Unexpected error from Arduino Main: {e}")


            """
            try : 
                data2 = self.arduinoSubData.readline().decode("utf-8").strip()
            except:
                self.show_error_message("Arduino sub 연결 끊어짐 오류", "Arduino sub와의 연결이 끊어졌습니다.")

            if data2:
                print("data2: ", data2)
                try:
                    state = data2.split("Security:")[1].strip()
                    print("data2 split", state)
                    if state == "2":
                        self.security_state = True
                    else:
                        self.security_state = False
                except (ValueError, IndexError):
                    print("data error:", data2)
                

            # arduinoMainData에서 데이터 읽기
            try :
                data = self.arduinoMainData.readline().decode('utf-8').strip()
            except:
                self.show_error_message("Arduino Main 연결 끊어짐 오류", "Arduino Main과의 연결이 끊어졌습니다.")
            if data:
                print("data", data)
                try:
                    if "Temperature:" in data and "Humidity:" in data and 'Water Level:' in data and 'Nutrition Water Level:' in data:
                        self.temperature_str = data.split("Temperature:")[1].split(",")[0].strip()
                        self.humidity_str = data.split("Humidity:")[1].split(",")[0].strip()
                        self.waterlevel_str = data.split("Water Level:")[1].split(",")[0].strip()
                        self.nutritionwaterlevel_str = data.split("Nutrition Water Level:")[1].split(",")[0].strip()

                        # 값 변환
                        self.temperature = int(self.temperature_str)
                        self.humidity = int(self.humidity_str)
                        self.soilhumidity = int(self.humidity_str)
                        self.waterlevel = int(self.waterlevel_str)
                        self.mapped_waterlevel = int(((self.waterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
                        self.nutritionwaterlevel = int(self.nutritionwaterlevel_str)
                        self.mapped_nutritionwaterlevel = int(((self.nutritionwaterlevel - 0) * (100 - 50) / (650 - 0)) + 50)
                except (ValueError, IndexError):
                    print("Data format error:", data)

            try:
                self.arduinoMainData = serial.Serial(main_usd_port, 9600)
                self.le_connection_status.setText("Connected to Arduino")
            except SerialException:
                self.arduinoData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
                self.le_connection_status.setText("Arduino connection failed")
                print("Failed to connect to Arduino")
            """
            time.sleep(0.1)  # CPU 사용량을 낮추기 위해 약간의 대기 시간을 추가

    def update_plot(self):
        self.find_normal_and_abnormal()

        ## 아두이노 연결 시도
        try:
            self.arduinoSubData = serial.Serial(sub_usd_port, 9600)
            self.le_connection_status.setText("Connected to Arduino Sub")
        except SerialException:
            self.arduinoSubData = serial.Serial(sub_usd_port, 9600)  # TinkerCAD serial 가능?
            self.le_connection_status.setText("Arduino Sub connection failed")
            print("Failed to connect to Arduino Sub")

        try:
            self.arduinoMainData = serial.Serial(main_usd_port, 9600)
            self.le_connection_status.setText("Connected to Arduino Main")
        except SerialException:
            self.arduinoMainData = serial.Serial(main_usd_port, 9600)  # TinkerCAD serial 가능?
            self.le_connection_status.setText("Arduino Main connection failed")
            print("Failed to connect to Arduino Main")

        # Update plot data
        self.temperature_data = np.roll(self.temperature_data, -1)
        self.temperature_data[-1] = self.temperature
        self.humidity_data = np.roll(self.humidity_data, -1)
        self.humidity_data[-1] = self.humidity

        # Update GUI elements
        self.le_temperature.setText(f"{self.temperature_str} °C")
        self.le_humidity.setText(f"{self.humidity_str} %")
        self.le_waterlevel.setText(f"{self.mapped_waterlevel} %")
        self.le_nutwaterlevel.setText(f"{self.mapped_nutritionwaterlevel} %")

        self.pbar_waterlevel.setValue(self.mapped_waterlevel)
        self.pbar_nutwaterlevel.setValue(self.mapped_nutritionwaterlevel)

        # Update graph lines
        self.temperaturePlotLine.setData(self.x, self.temperature_data)
        self.HumidityPlotLine.setData(self.x, self.humidity_data)

        farm_table = SmartFarmTable()
        current_time = time.time()
        if current_time - self.last_data_append_time >= 1.0:  # 1초마다 데이터 추가
            farm_table = SmartFarmTable()
            farm_table.append(self.mapped_waterlevel, self.mapped_nutritionwaterlevel,
                              self.soilhumidity, self.humidity, self.temperature,
                              self.security_state, self.normal_count, self.abnormal_count)
            self.last_data_append_time = current_time



    #######################################################################################로그인 및 gui관련 함수
    def show_error_message(self, title, message):
        #Qt 알림창을 통해 에러 메시지를 표시합니다.
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec_()

    def closeEvent(self, event):
        self.arduinoMainData.close()
        self.arduinoSubData.close()
        self.cap.release()
        event.accept()

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

    def changePage(self, index, active_button):
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
        """

        default_style_login = """
            QPushButton {
                background-color: rgb(243, 243, 243);
                color: black;
                border: none;
                text-align: left;
                padding: 5px 10px;
                border-radius: 5px;
            }
        """

        active_style = """
            QPushButton {
                background-color: #E6E47C;
                color: black;
                border: none;
                text-align: left;
                padding: 5px 10px;
                border-radius: 5px;
            }
        """

        self.DashboardBtn.setStyleSheet(default_style)
        self.LoginBtn.setStyleSheet(default_style_login)
        self.SettingsBtn.setStyleSheet(default_style)

        active_button.setStyleSheet(active_style)

        self.currentActiveButton = active_button

    def login(self):
        user_id = self.lineEdit_id.text()
        user_pw = self.lineEdit_password.text()

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black; }")  # 텍스트 색상을 검은색으로 설정

        if self.user_table.login(user_id, user_pw):
            msg.setWindowTitle("로그인 성공")
            msg.setText(f"{user_id}님 환영합니다!")
            msg.exec_()
            self.stackedWidget.setCurrentIndex(0)  # 대시보드 페이지로 이동
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
        msg.setStyleSheet("QLabel { color : black; }")  # 텍스트 색상을 검은색으로 설정

        if self.user_table.append_user(user_id, user_pw):
            msg.setWindowTitle("추가 성공")
            msg.setText(f"{user_id}가 추가되었습니다.")
            msg.exec_()
            self.load_data()  # 새로고침
        else:
            msg.setWindowTitle("추가 실패")
            msg.setText("중복된 ID가 있습니다.")
            msg.exec_()

    def update_user(self):
        user_id = self.id_input.text()
        user_pw = self.pw_input.text()

        self.user_table.update_user(user_id, user_pw)

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black; }")  # 텍스트 색상을 검은색으로 설정
        msg.setWindowTitle("수정 성공")
        msg.setText(f"{user_id}의 비밀번호가 수정되었습니다.")
        msg.exec_()

        self.load_data()  # 새로고침

    def delete_user(self):
        user_id = self.id_input.text()

        self.user_table.delete_user(user_id)

        msg = QMessageBox(self)
        msg.setStyleSheet("QLabel { color : black; }")  # 텍스트 색상을 검은색으로 설정
        msg.setWindowTitle("삭제 성공")
        msg.setText(f"{user_id}가 삭제되었습니다.")
        msg.exec_()

        self.load_data()  # 새로고침

    def load_selected_user(self, row, column):
        selected_id = self.tableWidget.item(row, 0).text()
        selected_pw = self.tableWidget.item(row, 1).text()
        self.id_input.setText(selected_id)
        self.pw_input.setText(selected_pw)

    def on_dial_change(self, value):
        """다이얼 값에 따라 색상을 변경합니다."""
        if value == 0:
            self.set_dial_2_color("gray") # Off
        elif value in {1, 2, 3}:
            self.set_dial_2_color("blue") # Cooling
        elif value in {4, 5, 6}:
            self.set_dial_2_color("red") # Heating
        elif value == 7:
            self.set_dial_2_color("yellow") # Auto

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

if __name__ == '__main__':
    App = QApplication(sys.argv)
    myWindow = SunnyMainWindow()
    myWindow.show()
    sys.exit(App.exec())
