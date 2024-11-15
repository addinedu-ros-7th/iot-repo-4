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

import resources_rc

import os
os.environ["QT_LOGGING_RULES"] = "*.debug=false"

from use_table import UserTable,SmartFarmTable
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths to the AI and gui_and_system directories
parent_dir_AI = os.path.join(current_dir, '..', 'AI')

# Add these directories to sys.path for module importing
sys.path.append(os.path.abspath(parent_dir_AI))


# GUI Theme
# import qdarktheme

# PyGt Desinger File
from PyQt5 import uic

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_file_path = os.path.join(current_dir, 'interface03.ui')

form_class = uic.loadUiType(ui_file_path)[0]

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
        self.setWindowTitle("FarmAI")

        self.arduinoData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
        
        # SET ATTRIBUTE PROPERTY

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
        #self.ControlBtn.clicked.connect(lambda: self.changePage(1, self.ControlBtn))
        #self.SensorBtn.clicked.connect(lambda: self.changePage(2, self.SensorBtn))
        self.LoginBtn.clicked.connect(lambda: self.changePage(1, self.LoginBtn))
        self.LogoutBtn.clicked.connect(lambda: self.changePage(0, self.DashboardBtn))
        self.SettingsBtn.clicked.connect(lambda: self.changePage(2, self.SettingsBtn))

        # 초기 화면을 대시보드 페이지로 설정
        self.stackedWidget.setCurrentIndex(0)
        self.changePage(0, self.DashboardBtn)

        # 다이얼 설정
        self.dial_2.setMinimum(0)
        self.dial_2.setMaximum(7)
        self.dial_2.valueChanged.connect(self.on_dial_change)
        # 다이얼 슬라이더 조작 시 페이지 전환 방지
        self.dial_2.sliderPressed.connect(lambda: None)
        self.set_dial_2_color("gray")  # 초기 색상 설정

        ###########

        #GUI Read
        self.dial_value = self.dial_2.value()
        serial.Serial(main_usd_port, 9600, timeout=1).write(str(self.dial_value).encode())

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


        # 업데이트 주기
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(2000)



    #DeepLearing

    # GUI Graph Plot 
    def read_arduino_data(self):
        if self.arduinoData.in_waiting > 0:
            data = self.arduinoData.readline().decode('utf-8').strip()
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
                self.arduinoData = serial.Serial(main_usd_port, 9600)
                self.le_connection_status.setText("Connected to Arduino")
            except SerialException:
                self.arduinoData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?
                self.le_connection_status.setText("Arduino connection failed")
                print("Failed to connect to Arduino")

            print(data)
        else:
            self.arduinoData = serial.Serial(main_usd_port, 9600) # TinkerCAD serial 가능?

    def update_plot(self):
        self.read_arduino_data()  # Call data-reading function

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
        farm_table.append(self.mapped_waterlevel , self.mapped_nutritionwaterlevel, self.soilhumidity, self.humidity, self.temperature , 0 , 0 , 0 )

    def closeEvent(self, event):
        self.arduinoData.close()
        self.cap.release()
        event.accept()
    
    def on_dial_value_changed(self, value):
        self.dial_value = value
        print(f"Dial value: {self.dial_value}")


    #GUI function

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
            self.set_dial_2_color("gray")
        elif value in {1, 2, 3}:
            self.set_dial_2_color("blue")
        elif value in {4, 5, 6}:
            self.set_dial_2_color("red")
        elif value == 7:
            self.set_dial_2_color("yellow")

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


if __name__ == '__main__':
    App = QApplication(sys. argv)
    # set_theme(App, theme='dark')
    myWindow = SunnyMainWindow()
    myWindow.show()
    sys.exit(App.exec())
