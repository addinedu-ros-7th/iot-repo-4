import os
from dotenv import load_dotenv
import pymysql
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
import bcrypt

load_dotenv()

class SmartFarmTable():
    _instance = None
    _last_slack_notification = None  # 마지막 Slack 메시지 전송 시간을 기록하는 변수

    def __new__(cls, *args, **kwargs):
        # 싱글톤 패턴: 이미 생성된 인스턴스가 없을 때만 인스턴스 생성
        if not cls._instance:
            cls._instance = super(SmartFarmTable, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 초기화 함수 호출
        self.init()

    def init(self):
        # 데이터베이스 연결 및 SMART_FARM 테이블 초기화
        # 이미 smart_farm 데이터베이스가 없다면 생성하고,
        # SMART_FARM 테이블이 없으면 생성합니다.
        self.conn = pymysql.connect(host='localhost', user='root', password= "whdgh29k05" ,charset='utf8')
        self.cursor = self.conn.cursor()

        self.cursor.execute("CREATE DATABASE IF NOT EXISTS smart_farm;")
        self.cursor.execute("USE smart_farm ;")

        sql ="""
        CREATE TABLE IF NOT EXISTS SMART_FARM(
            Time DATETIME PRIMARY KEY DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            Water_Level INT,
            Nutrient_Level INT,
            Soil_Humidity INT,
            Humidity INT,
            Degree INT,
            Security BOOL,
            Abnormal_Crop INT,
            Normal_Crop INT
        );
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def disconnect(self):
        # 데이터베이스 연결을 닫습니다.
        # 사용 후 자원을 해제하기 위해 호출되어야 합니다.
        self.cursor.close()
        self.conn.close()
    
    def append(self, Water_Level, Nutrient_Level, Soil_Humidity, Humidity, Degree, Security, Abnormal_Crop, Normal_Crop):
        # SMART_FARM 테이블에 새 데이터를 추가
        # 물 수위, 양분 수위, 토양 습도, 습도, 외부 온도, 보안 상태, 비정상 작물 개수, 정상 작물 개수를 받아 테이블에 삽입합니다.
        Security = "TRUE" if Security else "FALSE"
        self.cursor.execute(f"""
            INSERT INTO SMART_FARM (Water_Level, Nutrient_Level, Soil_Humidity, Humidity, Degree, Security, Abnormal_Crop, Normal_Crop) VALUES
                            ({Water_Level},{Nutrient_Level},{Soil_Humidity},{Humidity},{Degree},{Security}, {Abnormal_Crop}, {Normal_Crop})
            """)
        self.conn.commit()

        # Slack 메시지를 10분에 한 번씩만 전송하도록 조건 추가
        # if self._last_slack_notification is None or (datetime.now() - self._last_slack_notification) >= timedelta(minutes=10):
        #     # 환경 변수에서 Slack 토큰을 가져와 WebClient 객체 생성
        #     slack_token = os.getenv("SLACK_TOKEN")
        #     client = WebClient(token=slack_token)
        #     try:
        #         # 지정된 채널에 현재 상태를 Slack 메시지로 전송
        #         response = client.chat_postMessage(
        #             channel="C07UFQ6DTRD",  # 채널 ID를 입력합니다.
        #             text=f"""현재 
        #                 🌊 물 수위: {Water_Level} 
        #                 🥤 배양액 수위 : {Nutrient_Level} 
        #                 🌱 토양 습도 : {Soil_Humidity} 
        #                 💧 습도 : {Humidity} 
        #                 🌡️ 온도 : {Degree}
        #                 🔒 보안 상태 : {Security}
        #                 🌾 정상 작물 개수 : {Abnormal_Crop} 
        #                 🧪 비정상 작물 개수 : {Normal_Crop}
        #             """
        #         )
        #         # 메시지를 성공적으로 전송한 후 현재 시간을 _last_slack_notification에 저장
        #         self._last_slack_notification = datetime.now()  
        #     except SlackApiError as e:
        #         # Slack 메시지 전송 실패 시 에러 로깅
        #         assert e.response["error"]

    def get(self, count):
        # SMART_FARM 테이블에서 가장 최근의 데이터를 가져옴
        # 파라미터로 지정한 개수(count)만큼의 데이터를 내림차순으로 조회합니다.
        self.cursor.execute(f"SELECT * FROM SMART_FARM ORDER BY Time DESC LIMIT {count}")
        rows = self.cursor.fetchall()
        return rows



class UserTable():
    _instance = None

    def __new__(cls, *args, **kwargs):
        # 싱글톤 패턴: 이미 생성된 인스턴스가 없을 때만 인스턴스 생성
        if not cls._instance:
            cls._instance = super(UserTable, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 초기화 함수 호출
        self.init()

    def init(self):
        # 데이터베이스 연결 및 USER 테이블 초기화
        # 이미 smart_farm 데이터베이스가 없다면 생성하고,
        # USER 테이블이 없으면 생성합니다.
        # 기본적으로 'admin' 계정(ID: 'admin', PW: 'admin')이 없으면 생성됩니다.
        self.conn = pymysql.connect(host='localhost', user='root', password= "whdgh29k05", charset='utf8')
        self.cursor = self.conn.cursor()

        self.cursor.execute("CREATE DATABASE IF NOT EXISTS smart_farm;")
        self.cursor.execute("USE smart_farm ;")

        sql ="""
        CREATE TABLE IF NOT EXISTS USER(
            ID VARCHAR(32) PRIMARY KEY,
            PW VARCHAR(60)  -- bcrypt 해시 길이에 맞게 변경
        );
        """
        self.cursor.execute(sql)
        self.conn.commit()

        # 기본 admin 계정 추가 (해시된 비밀번호 사용)
        self.cursor.execute("SELECT * FROM USER WHERE ID = 'admin'")
        if not self.cursor.fetchall():
            hashed_pw = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute("INSERT INTO USER (ID, PW) VALUES (%s, %s)", ('admin', hashed_pw))
            self.conn.commit()

    def login(self, id, pw):
        # USER 테이블에서 사용자 로그인 확인
        # ID와 PW가 일치하는 사용자가 있는지 조회합니다.
        self.cursor.execute("SELECT PW FROM USER WHERE ID = %s", (id,))
        result = self.cursor.fetchall()
        if result:
            stored_pw = result[0]
            if bcrypt.checkpw(pw.encode('utf-8'), stored_pw.encode('utf-8')):
                slack_token = os.getenv("SLACK_TOKEN")
                client = WebClient(token=slack_token)
                try:
                    response = client.chat_postMessage(
                        channel="C07UFQ6DTRD",  # 채널 ID를 입력합니다.
                        text=f"""관리자가 로그인 했습니다."""
                    )
                except SlackApiError as e:
                    print(e)
                return True
        return False

    def append_user(self, id, pw):
        # USER 테이블에 새 사용자를 추가
        # 이미 동일한 ID가 존재하는 경우 False를 반환하고, 그렇지 않으면 추가 후 True를 반환합니다.
        self.cursor.execute("SELECT * FROM USER WHERE ID = %s", (id,))
        if not self.cursor.fetchall():
            hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute("INSERT INTO USER (ID, PW) VALUES (%s, %s)", (id, hashed_pw))
            self.conn.commit()
            return True
        return False
    
    def load_data(self):
        # 유저데이터를 불러옵니다.
        # 관리자 화면에 디스플레이용도
        self.cursor.execute("SELECT * FROM USER")
        return self.cursor.fetchall()

    def append_user(self, id, pw):
        #유저 데이터를 추가합니다.
        try:
            self.cursor.execute("INSERT INTO USER (ID, PW) VALUES (%s, %s)", (id, pw))
            self.conn.commit()
            return True
        except pymysql.IntegrityError:
            return False

    def update_user(self, id, pw):
        # 비밀번호 변경 시 해싱
        hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
        self.cursor.execute("UPDATE USER SET PW = %s WHERE ID = %s", (hashed_pw, id))
        self.conn.commit()

    def delete_user(self, id):
        #유저를 삭제합니다.
        self.cursor.execute("DELETE FROM USER WHERE ID = %s", (id,))
        self.conn.commit()


    def disconnect(self):
        # 데이터베이스 연결을 닫습니다.
        # 사용 후 자원을 해제하기 위해 호출되어야 합니다.
        self.cursor.close()
        self.conn.close()

