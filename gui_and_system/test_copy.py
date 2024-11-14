import numpy as np
import pandas as pd
import cv2
import sys
import pymysql
import sys
import time

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
# import torch
import numpy as np
from PyQt5 import uic
import cv2
import torch
import numpy as np
import serial  # serial 모듈 import
from serial.tools import list_ports
from use_table import UserTable, SmartFarmTable
import resources_rc  # 리소스 파일 import


import resources_rc

import os
os.environ["QT_LOGGING_RULES"] = "*.debug=false"

from use_table import UserTable,SmartFarmTable


# 현재 스크립트의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))

# 상위 디렉토리의 경로
parent_dir = os.path.join(current_dir, '..', 'AI')

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(parent_dir))

import detect_1  # 수정된 detect_1.py 파일 가져오기 (객체 검출 기능을 구현한 모듈)



# GUI Theme
# import qdarktheme

# PyGt Desinger File
from PyQt5 import uic

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_file_path = os.path.join(current_dir, 'interface03.ui')

form_class = uic.loadUiType(ui_file_path)[0]






# 사용 가능한 포트 리스트 가져오기
ports = serial.tools.list_ports.comports()

# PortInfo 객체에서 device 속성만 추출
portlist = [port.device for port in ports]

# 포트가 2개 이상인지 확인하여 각각 main_usd_port, sub_usd_port에 할당
if len(portlist) >= 2:
    main_usd_port = portlist[-1]
    sub_usd_port = portlist[-2]
elif len(portlist) == 1:
    main_usd_port = portlist[0]
    sub_usd_port = None  # sub_usd_port는 필요시 None으로 처리
else:
    raise Exception("사용 가능한 시리얼 포트를 찾을 수 없습니다")

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
        self.opt.imgsz = (480, 480)
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
class SunnyMainWindow(QMainWindow, form_class): # QWidget vs QMainWindow
    def __init__(self): 
        super(SunnyMainWindow, self).__init__()
        self.setupUi(self)

        self.arduinoMainData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
        self.arduinoSubData = serial.Serial(sub_usd_port, 9600) 

        


        # 검출된 객체 정보 저장 변수
        self.detection_data = []
        # 객체 검출 스레드 생성 및 시그널 연결
        self.detection_thread = DetectionThread()
        self.detection_thread.image_update.connect(self.update_image)
        self.detection_thread.detection_data_update.connect(self.update_detection_data)
        self.detection_thread.start()




            # SET ATTRIBUTE PROPERTY
        # Arduino connection status 
        self.le_connection_status.setText("Connecting to Arduino...")
    
        # 그래프가 들어가 attribute 생성
        self.humidity_canvas = pg.GraphicsLayoutWidget()
        # PyQt에서 만든 attribute에 삽입
        self.wdg_humidity.setLayout(QVBoxLayout())
        self.wdg_humidity.layout().addWidget(self.humidity_canvas)

        self.temperature_canvas = pg.GraphicsLayoutWidget()             
        self.wdg_temperature.setLayout(QVBoxLayout())
        self.wdg_temperature.layout().addWidget(self.temperature_canvas)

        self.HumidityPlot = self.humidity_canvas.addPlot()
        self.HumidityPlot.setXRange(0,20)
        self.HumidityPlot.setYRange(0,100)
        self.HumidityPlotLine = self.HumidityPlot.plot(pen= 'b') # 그래프라인만 따로 update 되기 떄문에

        self.temperaturePlot = self.temperature_canvas.addPlot()
        self.temperaturePlot.setXRange(0,20)
        self.temperaturePlot.setYRange(0,30)
        self.temperaturePlotLine = self.temperaturePlot.plot(pen= 'g') # 그래프라인만 따로 update 되기 떄문에

        self.x = np.arange(20)  # x range 20으로 고정
        self.temperature_data = np.zeros(20) # array로 저장
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


        # 업데이트 주기
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(2000)



    #DeepLearing
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
        

    def find_normal_and_abnormal (self):
        normal_count_ =0
        abnormal_count_ = 0
        for dictionary in self.detection_data:
            if dictionary["label"] == "normal":
                normal_count_ +=1
            else :
                abnormal_count_ +=1
        self.normal_count =  normal_count_ 
        self.abnormal_count = abnormal_count_
        


    def send_data_to_arduinoSubData(self, data): # reset 버튼에서 호출
        data_str = str(data) + "\n"  # 데이터 뒤에 줄바꿈 추가 (아두이노에서 한 줄 단위로 읽을 수 있도록)
        self.arduinoSubData.write(data_str.encode())  # 데이터를 인코딩하여 전송


    # GUI Graph Plot 
    def read_arduino_data(self):
        if self.arduinoSubData.in_waiting > 0:   # 아두이노 1에서
            
            data2 = self.arduinoSubData.readline().decode("utf-8").strip() # 데이터를 받음
            #print(data2)

            try :
                if "Security: " in data2 :    # 아두이노 1에서 받은데이터에
                    state = data2.split("Security:")[1].split("\n")[0].strip()
                    if state == "2":              # 상태값이 2일경우 보안 on 상태
                        self.security_state = True
                    else :                      # 상태값이 0이나 1일경우 보안 off 상태
                        self.security_state = False
            except (ValueError, IndexError):
                print("data error")


        if self.arduinoMainData.in_waiting > 0: # 아두이노 2에서
            data = self.arduinoMainData.readline().decode('utf-8').strip()
            try:
                if "Temperature:" in data and "Humidity:" in data and 'Water Level:' in data and 'Nutrition Water Level:' in data:
                    self.temperature_str = data.split("Temperature:")[1].split(",")[0].strip()
                    self.humidity_str = data.split("Humidity:")[1].split(",")[0].strip()
                    self.waterlevel_str = data.split("Water Level:")[1].split(",")[0].strip()
                    self.nutritionwaterlevel_str = data.split("Nutrition Water Level:")[1].split(",")[0].strip()

                    # Convert values
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
                self.arduinoMainData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
                self.le_connection_status.setText("Arduino connection failed")
                print("Failed to connect to Arduino")

            print(data)
        else:
            self.arduinoMainData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
        

    def update_plot(self):
        self.read_arduino_data()  # Call data-reading function
        self.find_normal_and_abnormal()


        print("normal count = ", self.normal_count)
        print("abnormal count = ", self.abnormal_count)
        print("security state = ", self.security_state)


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
        farm_table.append(self.mapped_waterlevel , self.mapped_nutritionwaterlevel, self.soilhumidity, self.humidity, self.temperature , self.security_state , self.normal_count , self.abnormal_count )

    def closeEvent(self, event):
        self.arduinoMainData.close()
        self.cap.release()
        event.accept()
    
if __name__ == '__main__':
    App = QApplication(sys. argv)
    # set_theme(App, theme='dark')
    myWindow = SunnyMainWindow()
    myWindow.show()
    sys.exit(App.exec())
