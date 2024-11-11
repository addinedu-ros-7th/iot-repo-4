import sys
import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap, QImage
import cv2
import detect_1  # 수정된 detect_1.py 파일 가져오기
import torch
import numpy as np

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('실시간 객체 검출')
        self.image_label = QLabel()
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.image_label)
        self.setLayout(self.layout)

        # 검출 옵션 설정
        self.opt = detect_1.parse_opt()
        self.opt.weights = 'best.pt'  # 가중치 파일 경로 설정
        self.opt.source = 0  # 웹캠 사용
        self.opt.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.opt.imgsz = (640, 640)
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

    def run(self):
        while True:
            ret, frame = self.cap.read()
            if ret:
                # 검출 수행
                results = self.detect_frame(frame)

                # 결과에서 이미지와 검출 정보를 가져옴
                if results:
                    result = results[0]  # 웹캠이므로 첫 번째 결과만 사용
                    im0 = result['image']

                    # OpenCV 이미지에서 PyQt 이미지로 변환
                    im0 = cv2.cvtColor(im0, cv2.COLOR_BGR2RGB)
                    h, w, ch = im0.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(im0.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)

                    # UI에 이미지 표시
                    self.image_label.setPixmap(pixmap)
                    QApplication.processEvents()
            else:
                break

    def detect_frame(self, frame):
        # 이미지 전처리
        img = cv2.resize(frame, self.imgsz)
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR -> RGB, HWC -> CHW
        img = np.ascontiguousarray(img)

        # 텐서로 변환
        im = torch.from_numpy(img).to(self.opt.device)
        im = im.half() if self.opt.half else im.float()  # uint8 -> fp16/32
        im /= 255  # 0 - 255 -> 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # 배치 차원 추가

        # 추론
        pred = self.model(im, augment=self.opt.augment, visualize=self.opt.visualize)

        # NMS 적용
        pred = detect_1.non_max_suppression(
            pred,
            self.opt.conf_thres,
            self.opt.iou_thres,
            self.opt.classes,
            self.opt.agnostic_nms,
            max_det=self.opt.max_det
        )

        # 결과 처리
        im0 = frame.copy()
        results = []
        for i, det in enumerate(pred):  # 이미지별로
            annotator = detect_1.Annotator(im0, line_width=self.opt.line_thickness, example=str(self.names))
            detections = []
            if len(det):
                # 박스 크기 조정
                det[:, :4] = detect_1.scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                for *xyxy, conf, cls in reversed(det):
                    if self.opt.hide_labels:
                        label = None
                    else:
                        label = f'{self.names[int(cls)]} {conf:.2f}' if not self.opt.hide_conf else f'{self.names[int(cls)]}'

                    annotator.box_label(xyxy, label, color=detect_1.colors(int(cls), True))
                    detection = {
                        'bbox': [int(coord.item()) for coord in xyxy],
                        'confidence': float(conf.item()),
                        'class': int(cls.item()),
                        'label': self.names[int(cls.item())]
                    }
                    detections.append(detection)

            im0 = annotator.result()
            results.append({
                'image': im0,
                'detections': detections
            })

        return results

    def closeEvent(self, event):
        self.cap.release()
        event.accept()

if __name__ == '__main__':
    # OpenCV의 Qt 플러그인 경로 제거 (충돌 방지)
    os.environ.pop("QT_PLUGIN_PATH", None)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.run()
    sys.exit(app.exec_())
