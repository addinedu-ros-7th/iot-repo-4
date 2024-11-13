import numpy as np
import pandas as pd
import cv2
import sys
import pymysql
import sys
import time
import test.LEE_class as LEE_class

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
#from AI import detect_1 as detect_1  # 수정된 detect_1.py 파일 가져오기 (객체 검출 기능을 구현한 모듈)
import torch
import numpy as np


# 현재 스크립트의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))

# 상위 디렉토리의 경로
parent_dir = os.path.join(current_dir, "..",'AI')

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(parent_dir))

import detect_1



# GUI Theme
# import qdarktheme

# PyGt Desinger File
form_class = uic.loadUiType("test.ui")[0]

# 포트 자동 인식
ports = serial.tools.list_ports.comports()
portlist = []
for port in ports:
    portlist.append(str(port))
main_usd_port = portlist[-1].split(' ')[0]

# Main Window
class SunnyMainWindow(QMainWindow, form_class): # QWidget vs QMainWindow
    def __init__(self): 
        super(SunnyMainWindow, self).__init__()
        self.setupUi(self)

        self.arduinoData = serial.Serial('/dev/ttyACM0', 9600) # TinkerCAD serial 가능?

            # SET ATTRIBUTE PROPERTY

        # WEBCAM
        # self.setWindowTitle('실시간 객체 검출')
        # self.ib_webcam = QLabel()
        # self.layout = QVBoxLayout()
        # self.layout.addWidget(self.ib_webcam)
        # self.setLayout(self.layout)

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
        self.temperaturePlot.setYRange(0,100)
        self.temperaturePlotLine = self.temperaturePlot.plot(pen= 'g') # 그래프라인만 따로 update 되기 떄문에

        self.x = np.arange(20)  # x range 20으로 고정
        self.temperature_data = np.zeros(20) # array로 저장
        self.humidity_data = np.zeros(20)

        # 업데이트 주기
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(50)


        #WebCam
        self.setWindowTitle('실시간 객체 검출')  # 윈도우 제목 설정

        self.detection_array = []  # 클래스 수준에서 빈 리스트로 초기화

        # 객체 검출 옵션 설정 및 모델 초기화
        self.opt = detect_1.parse_opt()
        self.opt.weights = '../AI/best.pt'
        self.opt.source = 0
        self.opt.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.opt.imgsz = (480  , 480)
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

    #DeepLearing

    # 실시간 객체 검출 실행 메서드
    def run(self):
        while True:
            ret, frame = self.cap.read()  # 프레임 읽기
            if ret:
                # 프레임에 대해 객체 검출 수행
                results = self.detect_frame(frame)

                # 결과에서 검출된 이미지와 정보 가져오기
                if results:
                    result = results[0]  # 첫 번째 프레임 결과 사용
                    im0 = result['image']
                    detections = result['detections']  # 검출된 객체 정보

                    # 검출된 객체 정보를 배열 형태로 출력
                    self.detection_array = []
                    for detection in detections:
                        self.detection_array.append({
                            'bbox': detection['bbox'],
                            'confidence': detection['confidence'],
                            'class': detection['class'],
                            'label': detection['label']
                        })
                    # print(self.detection_array)  # 배열 형태로 출력

                    # OpenCV 이미지를 PyQt 이미지로 변환하여 표시
                    im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)  # BGR을 RGB로 변환
                    h, w, ch = im0.shape  # 이미지의 높이, 너비, 채널 정보
                    bytes_per_line = ch * w  # 한 줄당 바이트 수 계산
                    qt_image = QImage(im0.data, w, h, bytes_per_line, QImage.Format_RGB888)  # PyQt 이미지 생성
                    pixmap = QPixmap.fromImage(qt_image)  # QPixmap 객체로 변환

                    pixmap = pixmap.scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

                    # UI에 이미지 표시
                    self.lb_webcam.setPixmap(pixmap)  # 이미지 QLabel에 표시
                    QApplication.processEvents()  # UI 갱신
            else:
                break

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


    # GUI Graph Plot 
    def update_plot(self):
            if self.arduinoData.in_waiting > 0:
                data = self.arduinoData.readline().decode('utf-8').strip()
                try:
                    # 데이터 읽어오기
                    if "Temperature:" in data and "Humidity:" in data and 'Water Level' in data:
                        temperature_str = data.split("Temperature:")[1].split("\n")[0].strip()
                        humidity_str = data.split("Humidity:")[1].split("\n")[0].strip()
                        waterlevel_str = data.split("Water Level:")[1].split("\n")[0].strip()
                        temperature = int(temperature_str) # float??
                        humidity = int(humidity_str) # float??
                        mapped_waterlevel = self.map_water_level(int(waterlevel_str))

    

                        self.temperature_data = np.roll(self.temperature_data, -1) # 마지막 값 자리 비우기 (옆으로 밀기)
                        self.temperature_data[-1] = temperature # 마지막 값 업데이트
                        self.humidity_data = np.roll(self.humidity_data, -1)
                        self.humidity_data[-1] = humidity

                        self.le_temperature.setText(f"{temperature_str} °C")
                        self.le_humidity.setText(f"{humidity_str} %")
                        self.le_waterlevel.setText(f"{mapped_waterlevel} %")
                        
                        self.pbar_waterlevel.setValue()
                        # 그래프 라인 업데이트
                        self.temperaturePlotLine.setData(self.x, self.temperature_data)
                        self.HumidityPlotLine.setData(self.x, self.humidity_data)
                except (ValueError, IndexError):
                    print("Data format error:", data)
            # LEE_class.InsertDataIntoDB().append( , , , , , , , )

    def closeEvent(self, event):
        self.arduinoData.close()
        self.cap.release()
        event.accept()

    def map_water_level(value):
        mapped_value = ((value - 0) * (100 - 50) / (1023 - 0)) + 50
        return mapped_value
    
if __name__ == '__main__':
    App = QApplication(sys. argv)
    # set_theme(App, theme='dark')
    myWindow = SunnyMainWindow()
    myWindow.show()
    sys.exit(App.exec())
