import sys
import os


from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, Qt, QThread, pyqtSignal, QTimer
from PyQt5 import uic
import PyQt5.QtCore as QtCore


import cv2
import torch
import numpy as np
import serial  # serial 모듈 import
from serial.tools import list_ports
from use_table import UserTable, SmartFarmTable
import resources_rc  # 리소스 파일 import



# 현재 스크립트의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))

# 상위 디렉토리의 경로
parent_dir = os.path.join(current_dir, '..', 'AI')

# 상위 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(parent_dir))

import detect_1  # 수정된 detect_1.py 파일 가져오기 (객체 검출 기능을 구현한 모듈)



# ui 파일 임포트
from_class = uic.loadUiType("interface01.ui")[0]




ports = list_ports.comports() # 포트 자동인식
portlist = []
for port in ports:
    portlist.append(str(port))
main_usd_port = portlist[-1].split(' ')[0]



class DetectionThread(QThread):
    image_update = pyqtSignal(QImage)

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

                    # 검출된 객체 정보를 배열 형태로 출력 (필요에 따라 사용)
                    # self.detection_array = []
                    # for detection in detections:
                    #     self.detection_array.append({
                    #         'bbox': detection['bbox'],
                    #         'confidence': detection['confidence'],
                    #         'class': detection['class'],
                    #         'label': detection['label']
                    #     })

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


class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("FarmAI")

        self.arduinoData1 = serial.Serial('/dev/ttyACM0', 9600)
        #self.arduinoData2 = serial.Serial('/dev/ttyACM1', 9600)


        # 업데이트 주기
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot )
        self.timer.start(50)



        # 스타일시트를 사용하여 배경을 투명하게 설정
        self.leftMenuSubContainer.setStyleSheet("background-color: transparent;")
        # self.SettingsBtn.setStyleSheet("background-color: transparent;")  # "관리자" 버튼 배경도 투명하게 설정

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
            "ControlBtn": "제어설정",
            "SensorBtn": "센서 데이터",
            "LogoutBtn": "로그아웃",
            "SettingsBtn": "관리자"
        }

        # 로그인 버튼 클릭 이벤트 연결
        self.pushButton_login.clicked.connect(self.login)

        # 버튼 클릭 시 메뉴를 확장/축소하는 이벤트 연결
        self.menuBtn.clicked.connect(self.toggleMenu)

        # 버튼 클릭 시 페이지 전환 및 강조 효과 적용
        self.DashboardBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.ControlBtn.clicked.connect(lambda: self.changePage(1, self.ControlBtn))
        self.SensorBtn.clicked.connect(lambda: self.changePage(2, self.SensorBtn))
        self.LoginBtn.clicked.connect(lambda: self.changePage(3, self.LoginBtn))
        self.LogoutBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.SettingsBtn.clicked.connect(lambda: self.changePage(4, self.SettingsBtn))

        # 초기 화면을 대시보드 페이지로 설정
        self.stackedWidget.setCurrentIndex(0)
        self.changePage(0, self.DashboardBtn)

        # 현재 활성화된 버튼을 추적하기 위한 변수
        self.currentActiveButton = None

        # 객체 검출 스레드 생성 및 시그널 연결
        self.detection_thread = DetectionThread()
        self.detection_thread.image_update.connect(self.update_image)
        self.detection_thread.start()

    def closeEvent(self, event):
        # 스레드 정지 및 자원 해제
        self.detection_thread.stop()
        event.accept()

    def update_image(self, qt_image):
        # 이미지 레이블에 업데이트
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

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
        self.ControlBtn.setStyleSheet(default_style)
        self.SensorBtn.setStyleSheet(default_style)
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



################################################################################################################



    def update_plot(self):
            
        if self.arduinoData1.in_waiting > 0:

            data2 = self.arduinoData1.readline().decode("utf-8").strip()
            
            try :
                if "Security: " in data2 :
                    print(data2[-1:])
                    if
            except (ValueError, IndexError):
                print("data error")

        #if self.arduinoData2.in_waiting > 0:
            #data = self.arduinoData2.readline().decode('utf-8').strip()
            """
            #아두이노 1 처리
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
            # SmartFarmTable.InsertDataIntoDB().append( , , , , , , , )
                """


                

    def closeEvent(self, event):
        self.arduinoData.close()
        self.cap.release()
        event.accept()

    def map_water_level(value):
        mapped_value = ((value - 0) * (100 - 50) / (1023 - 0)) + 50
        return mapped_value


if __name__ == "__main__":
    # OpenCV의 Qt 플러그인 경로 제거 (충돌 방지)
    os.environ.pop("QT_PLUGIN_PATH", None)

    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
