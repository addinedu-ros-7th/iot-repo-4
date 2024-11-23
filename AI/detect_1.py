# detect_1.py

import argparse
import os
import sys
from pathlib import Path

import torch

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 루트 디렉토리
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # ROOT를 PATH에 추가
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # 상대 경로

from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadStreams
from utils.general import (LOGGER, check_img_size, check_imshow, colorstr,
                           non_max_suppression, scale_boxes, xyxy2xywh)
from utils.plots import Annotator, colors
from utils.torch_utils import select_device, smart_inference_mode


@smart_inference_mode()
def run(
        weights=ROOT / 'yolov5s.pt',  # 모델 경로
        source=ROOT / 'data/images',  # 파일/디렉토리/URL/글롭/웹캠
        data=ROOT / 'data/coco128.yaml',  # 데이터셋 yaml 경로
        imgsz=(640, 640),  # 입력 이미지 크기
        conf_thres=0.25,  # 신뢰도 임계값
        iou_thres=0.45,  # NMS IoU 임계값
        max_det=1000,  # 이미지당 최대 검출 수
        device='',  # cuda 장치 ('0' 또는 'cpu')
        classes=None,  # 클래스 필터
        agnostic_nms=False,  # 클래스 무관 NMS
        augment=False,  # 증강 추론
        visualize=False,  # 특성 맵 시각화
        line_thickness=3,  # 경계 상자 두께
        hide_labels=False,  # 레이블 숨기기
        hide_conf=False,  # 신뢰도 숨기기
        half=False,  # FP16 절반 정밀도 사용
        dnn=False,  # OpenCV DNN 사용
        vid_stride=1,  # 비디오 프레임 간격
):
    source = str(source)
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://')) and not Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)

    # 모델 로드
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # 이미지 크기 확인

    # 데이터 로더 설정
    if webcam:
        view_img = check_imshow(warn=True)
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = len(dataset)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
        bs = 1

    # 추론 실행
    model.warmup(imgsz=(1 if pt else bs, 3, *imgsz))  # 워밍업
    results = []
    for path, im, im0s, vid_cap, s in dataset:
        im = torch.from_numpy(im).to(device)
        im = im.half() if model.fp16 else im.float()  # uint8 -> fp16/32
        im /= 255  # 0 - 255 -> 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # 배치 차원 추가

        # 추론
        pred = model(im, augment=augment, visualize=visualize)

        # NMS 적용
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # 결과 처리
        for i, det in enumerate(pred):  # 이미지별로
            im0 = im0s[i].copy() if webcam else im0s.copy()
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            detections = []
            if len(det):
                # 박스 크기 조정
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                for *xyxy, conf, cls in reversed(det):
                    if hide_labels:
                        label = None
                    else:
                        label = f'{names[int(cls)]} {conf:.2f}' if not hide_conf else f'{names[int(cls)]}'

                    annotator.box_label(xyxy, label, color=colors(int(cls), True))
                    detection = {
                        'bbox': [int(coord.item()) for coord in xyxy],
                        'confidence': float(conf.item()),
                        'class': int(cls.item()),
                        'label': names[int(cls.item())]
                    }
                    detections.append(detection)

            im0 = annotator.result()
            results.append({
                'image': im0,
                'detections': detections
            })

        if not webcam:
            break  # 비웹캠 소스는 첫 프레임만 처리

    return results


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default=ROOT / 'yolov5s.pt', help='모델 경로')
    parser.add_argument('--source', type=str, default=ROOT / 'data/images', help='파일/디렉토리/URL/글롭/웹캠')
    parser.add_argument('--data', type=str, default=ROOT / 'data/coco128.yaml', help='데이터셋 yaml 경로')
    parser.add_argument('--imgsz', '--img', '--img-size', nargs='+', type=int, default=[640], help='입력 이미지 크기')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='신뢰도 임계값')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IoU 임계값')
    parser.add_argument('--max-det', type=int, default=1000, help='이미지당 최대 검출 수')
    parser.add_argument('--device', default='', help='cuda 장치')
    parser.add_argument('--classes', nargs='+', type=int, help='클래스 필터')
    parser.add_argument('--agnostic-nms', action='store_true', help='클래스 무관 NMS')
    parser.add_argument('--augment', action='store_true', help='증강 추론')
    parser.add_argument('--visualize', action='store_true', help='특성 맵 시각화')
    parser.add_argument('--line-thickness', default=3, type=int, help='경계 상자 두께')
    parser.add_argument('--hide-labels', default=False, action='store_true', help='레이블 숨기기')
    parser.add_argument('--hide-conf', default=False, action='store_true', help='신뢰도 숨기기')
    parser.add_argument('--half', action='store_true', help='FP16 절반 정밀도 사용')
    parser.add_argument('--dnn', action='store_true', help='OpenCV DNN 사용')
    parser.add_argument('--vid-stride', type=int, default=1, help='비디오 프레임 간격')
    opt = parser.parse_args()
    return opt


def main(opt):
    results = run(**vars(opt))
    return results


# if __name__ == "__main__":
#     opt = parse_opt()
#     main(opt)
