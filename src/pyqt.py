# 필수 모듈 import
import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
import cv2
import detect_1  # 수정된 detect_1.py 파일 가져오기 (객체 검출 기능을 구현한 모듈)
import torch
import numpy as np

# 메인 윈도우 클래스 정의
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('실시간 객체 검출')  # 윈도우 제목 설정
        self.image_label = QLabel()  # 이미지 출력할 QLabel 생성
        self.layout = QVBoxLayout()  # 세로 레이아웃 생성
        self.layout.addWidget(self.image_label)  # 레이아웃에 이미지 QLabel 추가
        self.setLayout(self.layout)  # 위젯 레이아웃 설정

        # 객체 검출 옵션 설정
        self.opt = detect_1.parse_opt()  # detect_1 모듈에서 옵션을 가져옴
        self.opt.weights = 'best.pt'  # 학습된 모델 가중치 파일 지정
        self.opt.source = 0  # 웹캠(카메라)을 데이터 소스로 설정
        self.opt.device = 'cuda' if torch.cuda.is_available() else 'cpu'  # GPU(CUDA) 또는 CPU 선택
        self.opt.imgsz = (640, 640)  # 입력 이미지 크기 설정
        self.opt.conf_thres = 0.25  # 검출 신뢰도 임계값 설정
        self.opt.iou_thres = 0.45  # NMS의 IOU 임계값 설정
        self.opt.classes = None  # 특정 클래스만 검출할지 여부 (None은 전체 클래스 포함)
        self.opt.agnostic_nms = False  # 클래스 무관 NMS 사용 여부
        self.opt.half = False  # FP16(반정밀도) 사용 여부

        # 모델 초기화
        self.model = detect_1.DetectMultiBackend(
            self.opt.weights,
            device=self.opt.device,
            dnn=self.opt.dnn,
            data=self.opt.data,
            fp16=self.opt.half
        )  # 객체 검출 모델을 불러옴
        self.stride = self.model.stride  # 모델의 stride 값 가져오기
        self.names = self.model.names  # 클래스 이름들 가져오기
        self.imgsz = detect_1.check_img_size(self.opt.imgsz, s=self.stride)  # 이미지 크기 유효성 체크

        # 웹캠 열기
        self.cap = cv2.VideoCapture(self.opt.source)  # 0번 카메라 연결

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

                    # OpenCV 이미지를 PyQt 이미지로 변환하여 표시
                    im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)  # BGR을 RGB로 변환
                    h, w, ch = im0.shape  # 이미지의 높이, 너비, 채널 정보
                    bytes_per_line = ch * w  # 한 줄당 바이트 수 계산
                    qt_image = QImage(im0.data, w, h, bytes_per_line, QImage.Format_RGB888)  # PyQt 이미지 생성
                    pixmap = QPixmap.fromImage(qt_image)  # QPixmap 객체로 변환

                    # UI에 이미지 표시
                    self.image_label.setPixmap(pixmap)  # 이미지 QLabel에 표시
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

    # 윈도우 닫기 이벤트 처리 메서드
    def closeEvent(self, event):
        self.cap.release()  # 웹캠 해제
        event.accept()  # 창 닫기 허용

# 프로그램 시작점
if __name__ == '__main__':
    # OpenCV의 Qt 플러그인 경로 제거 (충돌 방지)
    os.environ.pop("QT_PLUGIN_PATH", None)

    app = QApplication(sys.argv)  # Qt 애플리케이션 생성
    window = MainWindow()  # MainWindow 인스턴스 생성
    window.show()  # 윈도우 표시
    window.run()  # 객체 검출 실행
    sys.exit(app.exec_())  # 앱 실행 후 종료
