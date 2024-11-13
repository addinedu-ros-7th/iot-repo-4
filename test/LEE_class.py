import serial
import pymysql
from serial import SerialException


class InsertDataIntoDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InsertDataIntoDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.init_connection()

    def init_connection(self):
        try:
            # Connect to the database and initialize the table
            self.conn = pymysql.connect(host='localhost', user='root', password='9092', charset='utf8')
            self.cursor = self.conn.cursor()
            self.cursor.execute("CREATE DATABASE IF NOT EXISTS smart_farm;")
            self.cursor.execute("USE smart_farm;")
            self.create_table()
            print("Database and table initialized successfully.")
        except pymysql.MySQLError as e:
            print(f"Database connection error: {e}")

    def create_table(self):
        try:
            sql = """
            CREATE TABLE IF NOT EXISTS SMART_FARM(
                Time TIMESTAMP PRIMARY KEY DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                Water_Level INT,
                Nutrient_Level INT,
                Soil_Humidity INT,
                Humidity INT,
                Temperature INT,
                Security BOOL,
                Abnormal_Crop INT,
                Normal_Crop INT
            );
            """
            self.cursor.execute(sql)
            self.conn.commit()
        except pymysql.MySQLError as e:
            print(f"Table creation error: {e}")

    def reconnect_if_needed(self):
        try:
            # Check if the connection is still open and reconnect if necessary
            if not self.conn.open:
                print("Reconnecting to the database...")
                self.init_connection()
            elif self.cursor is None:
                self.cursor = self.conn.cursor()
        except pymysql.MySQLError as e:
            print(f"Reconnection error: {e}")
            self.init_connection()

    def append(self, water_level, nutrient_level, soil_humidity, humidity, temperature, security, abnormal_crop, normal_crop):
        try:
            self.reconnect_if_needed()
            security = 1 if security else 0
            sql = """
                REPLACE INTO SMART_FARM (Water_Level, Nutrient_Level, Soil_Humidity, Humidity, Temperature, Security, Abnormal_Crop, Normal_Crop)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.cursor.execute(sql, (water_level, nutrient_level, soil_humidity, humidity, temperature, security, abnormal_crop, normal_crop))
            self.conn.commit()
            print("Data appended to database:", humidity, temperature)
        except pymysql.MySQLError as e:
            print(f"Error inserting data: {e}")
            self.conn.rollback()

        def disconnect(self):
            try:
                self.cursor.close()
                self.conn.close()
                print("Database connection closed.")
            except pymysql.MySQLError as e:
                print(f"Error closing database connection: {e}")

    def get(self, count):
        try:
            self.reconnect_if_needed()
            self.cursor.execute(f"SELECT * FROM SMART_FARM ORDER BY Time DESC LIMIT {count}")
            return self.cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching data: {e}")
            return []
        
    def disconnect(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("Database connection closed.")
        except pymysql.MySQLError as e:
            print(f"Error closing database connection: {e}")

class TempHumCollector:
    def __init__(self, db_table):
        self.db_table = db_table
        self.stop_flag = False

    def serial_start(self, port, baud_rate):
        try:
            self.ser = serial.Serial(port, baud_rate)
            print("Connection to serial port successful!")
        except SerialException as e:
            print(f"Connection error: {e}")
            self.stop_flag = True

    def data_collect(self):
        temp_val, humid_val = None, None
        while not self.stop_flag:
            try:
                if self.ser.readable():
                    res = self.ser.readline()
                    res_decode = res.decode().strip()
                    print("Data received from serial:", res_decode)

                    # Process temperature and humidity readings
                    if res_decode.startswith("tem"):
                        temp_val_raw = res_decode[3:]
                        temp_val = round(float(temp_val_raw) / 100, 2)
                    elif res_decode.startswith("hum"):
                        humid_val_raw = res_decode[3:]
                        humid_val = round(float(humid_val_raw) / 100, 2)

                        # Insert data only if both values are available
                        if temp_val is not None and humid_val is not None:
                            print("Data ready for insertion:", temp_val, humid_val)
                            self.db_table.append(0, 0, 0, humid_val, temp_val, True, 0, 0)
                            temp_val, humid_val = None, None
            except (ValueError, IndexError) as e:
                print(f"Data parsing error: {e}")
            except SerialException as e:
                print(f"Serial reading error: {e}")
                self.stop_flag = True
                break

    def stop_collecting(self):
        self.stop_flag = True
        self.ser.close()
        print("Stopped data collection.")
