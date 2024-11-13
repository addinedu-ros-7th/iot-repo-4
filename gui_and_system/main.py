import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
from PyQt5 import uic
import pymysql

import resources_rc  # 리소스 파일 import

from_class = uic.loadUiType("interface01.ui")[0]


class UserTable():
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UserTable, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.init()

    def init(self):
        self.conn = pymysql.connect(host='localhost', user='root', password='whdgh29k05', charset='utf8')
        self.cursor = self.conn.cursor()

        self.cursor.execute("CREATE DATABASE IF NOT EXISTS smart_farm;")
        self.cursor.execute("USE smart_farm ;")

        sql ="""
        CREATE TABLE IF NOT EXISTS USER(
            ID VARCHAR(32) PRIMARY KEY,
            PW VARCHAR(32)
        );
        """
        self.cursor.execute(sql)
        self.conn.commit()

        # 기본 admin 계정이 없으면 추가
        self.cursor.execute("SELECT * FROM USER")
        if not self.cursor.fetchall():
            self.cursor.execute("INSERT INTO USER VALUES ('admin', 'admin')")
            self.conn.commit()

    def login(self, id, pw):
        self.cursor.execute("SELECT * FROM USER WHERE ID = %s AND PW = %s", (id, pw))
        return bool(self.cursor.fetchall())

    def load_data(self):
        self.cursor.execute("SELECT * FROM USER")
        return self.cursor.fetchall()

    def append_user(self, id, pw):
        try:
            self.cursor.execute("INSERT INTO USER (ID, PW) VALUES (%s, %s)", (id, pw))
            self.conn.commit()
            return True
        except pymysql.IntegrityError:
            return False

    def update_user(self, id, pw):
        self.cursor.execute("UPDATE USER SET PW = %s WHERE ID = %s", (pw, id))
        self.conn.commit()

    def delete_user(self, id):
        self.cursor.execute("DELETE FROM USER WHERE ID = %s", (id,))
        self.conn.commit()

    def disconnect(self):
        self.cursor.close()
        self.conn.close()


class WindowClass(QMainWindow, from_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("FarmAI")

        # 스타일시트를 사용하여 배경을 투명하게 설정
        self.leftMenuSubContainer.setStyleSheet("background-color: transparent;")
        #self.SettingsBtn.setStyleSheet("background-color: transparent;")  # "관리자" 버튼 배경도 투명하게 설정

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())

