import argparse
import csv
import os
# import platform
import shutil
import sys
from pathlib import Path
import torch

FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from ultralytics.utils.plotting import Annotator, colors, save_one_box
from models.common import DetectMultiBackend
from utils.dataloaders import IMG_FORMATS, VID_FORMATS, LoadImages, LoadScreenshots, LoadStreams
from utils.general import (
    LOGGER,
    Profile,
    check_file,
    check_img_size,
    check_imshow,
    check_requirements,
    colorstr,
    cv2,
    increment_path,
    non_max_suppression,
    print_args,
    scale_boxes,
    strip_optimizer,
    xyxy2xywh,
)
from utils.torch_utils import select_device, smart_inference_mode


@smart_inference_mode()
def run(
        weights=ROOT / "yolov5s.pt",  # model path or triton URL
        source=ROOT,  # file/dir/URL/glob/screen/0(webcam)
        data=None,  # optional dataset.yaml path
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.25,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device="",  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img=False,  # show results
        save_txt=True,  # save results to *.txt
        save_format=0,  # save boxes coordinates in YOLO format or Pascal-VOC format (0 for YOLO and 1 for Pascal-VOC)
        save_csv=False,  # save results in CSV format
        save_conf=False,  # save confidences in --save-txt labels
        save_crop=False,  # save cropped prediction boxes
        nosave=False,  # do not save images/videos
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        update=False,  # update all models
        project=ROOT / "runs/detect",  # save results to project/name
        name="exp",  # save results to project/name
        exist_ok=False,  # existing project/name ok, do not increment
        line_thickness=3,  # bounding box thickness (pixels)
        hide_labels=False,  # hide labels
        hide_conf=False,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
        vid_stride=1,  # video frame-rate stride
):
    global c1_array, c5_array, c1, c5, conf_c1, conf_c5, x1_c1, x1_c5, y1_c1, y1_c5
    global c0, c2, c3, c4, conf_c0, conf_c2, conf_c3, conf_c4, x1_c0, x1_c2, x1_c3, x1_c4, y1_c0, y1_c2, y1_c3, y1_c4
    global w1_c0, w1_c2, w1_c3, w1_c4, h1_c0, h1_c2, h1_c3, h1_c4
    global im0
    global line0, xywh_c0, line2, xywh_c2, line3, xywh_c3, line4, xywh_c4, line1, xywh_c1, line5, xywh_c5

    source = str(source)
    save_img = not nosave and not source.endswith(".txt")  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)

    if is_file:
        source = check_file(source)  # download

    # Directories
    # save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
    save_dir = Path(project) / name
    (save_dir / "labels" if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir
    if not os.path.exists(str(save_dir) + '/labels'):  # mkdir if not exist
        os.makedirs(str(save_dir) + '/labels')

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn, data=data, fp16=half)
    stride, names, pt = model.stride, model.names, model.pt
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Dataloader
    bs = 1  # batch_size
    dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt, vid_stride=vid_stride)
    # vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    model.warmup(imgsz=(1 if pt or model.triton else bs, 3, *imgsz))  # warmup
    seen, windows, dt = 0, [], (Profile(device=device), Profile(device=device), Profile(device=device))
    for path, im, im0s, vid_cap, s in dataset:
        with dt[0]:
            im = torch.from_numpy(im).to(model.device)
            im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
            im /= 255  # 0 - 255 to 0.0 - 1.0
            if len(im.shape) == 3:
                im = im[None]  # expand for batch dim
            if model.xml and im.shape[0] > 1:
                ims = torch.chunk(im, im.shape[0], 0)

        # Inference
        with dt[1]:
            visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
            if model.xml and im.shape[0] > 1:
                pred = None
                for image in ims:
                    if pred is None:
                        pred = model(image, augment=augment, visualize=visualize).unsqueeze(0)
                    else:
                        pred = torch.cat((pred, model(image, augment=augment, visualize=visualize).unsqueeze(0)), dim=0)
                pred = [pred, None]
            else:
                pred = model(im, augment=augment, visualize=visualize)
        # NMS
        with dt[2]:
            pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Define the path for the CSV file
        csv_path = save_dir / "predictions.csv"

        # Create or append to the CSV file
        def write_to_csv(image_name, prediction, confidence):
            """Writes prediction data for an image to a CSV file, appending if the file exists."""
            data = {"Image Name": image_name, "Prediction": prediction, "Confidence": confidence}
            with open(csv_path, mode="a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                if not csv_path.is_file():
                    writer.writeheader()
                writer.writerow(data)

        im0_000 = ''
        detected_object = False

        # Process predictions
        for i, det in enumerate(pred):  # per image
            p, im0, frame = path, im0s.copy(), getattr(dataset, "frame", 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / "labels" / p.stem) + ("" if dataset.mode == "image" else f"_{frame}")  # im.txt
            s += "{:g}x{:g} ".format(*im.shape[2:])  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))

            c1 = c5 = c0 = c2 = c3 = c4 = False
            conf_c0 = x1_c0 = y1_c0 = w1_c0 = h1_c0 = 0
            conf_c2 = x1_c2 = y1_c2 = w1_c2 = h1_c2 = 0
            conf_c3 = x1_c3 = y1_c3 = w1_c3 = h1_c3 = 0
            conf_c4 = x1_c4 = y1_c4 = w1_c4 = h1_c4 = 0
            conf_c1 = x1_c1 = y1_c1 = w1_c1 = h1_c1 = 0
            conf_c5 = x1_c5 = y1_c5 = w1_c5 = h1_c5 = 0
            c1_array = []
            c5_array = []

            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()

                '''
                # class names
                names: ['left_kidney' -              0,
                        'stone' -                    1,
                        'right_kidney' -             2,
                        'left_kidney_pieloectasy' -  3,
                        'right_kidney_pieloectasy' - 4,
                        'staghorn_stones' -          5]
                '''

                # Print results
                for c in det[:, 5].unique():
                    n = (det[:, 5] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                    x1, y1, w1, h1, = xywh
                    c = int(cls)
                    if c == 1 and conf >= 0.5:  # stone type stone
                        c1 = True
                        conf_c1 = conf
                        line1 = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        xywh_c1 = xyxy
                        label1 = f'{names[1]} {conf_c1:.2f}'
                        with open(f'{txt_path}.txt', 'a') as f:
                            f.write(('%g ' * len(line1)).rstrip() % line1 + '\n')
                        annotator.box_label(xywh_c1, label1, color=colors(c, True))
                    elif c == 5 and conf >= 0.5:  # stone type staghorn_stones
                        c5 = True
                        conf_c5 = conf
                        line5 = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        xywh_c5 = xyxy
                        label5 = f'{names[1]} {conf_c5:.2f}'
                        with open(f'{txt_path}.txt', 'a') as f:
                            f.write(('%g ' * len(line5)).rstrip() % line5 + '\n')
                        annotator.box_label(xywh_c5, label5, color=colors(c, True))
                    elif c == 0 and \
                            0.55 < x1 < 0.704613 and 0.248879 < y1 < 0.66704 and w1 * h1 > w1_c0 * h1_c0:
                        c0 = True
                        conf_c0 = conf
                        x1_c0 = x1
                        y1_c0 = y1
                        w1_c0 = w1
                        h1_c0 = h1
                        x1y1w1h1 = x1_c0, y1_c0, w1_c0, h1_c0
                        line0 = (cls, *xywh, conf) if save_conf else (cls, *xywh)
                        xywh_c0 = xyxy
                    elif c == 3 and \
                            0.55 < x1 < 0.704613 and 0.248879 < y1 < 0.66704 and w1 * h1 > w1_c3 * h1_c3:
                        c3 = True
                        conf_c3 = conf
                        x1_c3 = x1
                        y1_c3 = y1
                        w1_c3 = w1
                        h1_c3 = h1
                        line3 = (cls, *xywh, conf) if save_conf else (cls, *xywh)
                        xywh_c3 = xyxy
                    elif c == 2 and \
                            0.2 < x1 < 0.45 and 0.2 < y1 < 0.804613 and w1 * h1 > w1_c2 * h1_c2:
                        c2 = True
                        conf_c2 = conf
                        x1_c2 = x1
                        y1_c2 = y1
                        w1_c2 = w1
                        h1_c2 = h1
                        line2 = (cls, *xywh, conf) if save_conf else (cls, *xywh)
                        xywh_c2 = xyxy
                    elif c == 4 and \
                            0.2 < x1 < 0.45 and 0.2 < y1 < 0.804613 and w1 * h1 > w1_c4 * h1_c4:
                        c4 = True
                        conf_c4 = conf
                        x1_c4 = x1
                        y1_c4 = y1
                        w1_c4 = w1
                        h1_c4 = h1
                        line4 = (cls, *xywh, conf) if save_conf else (cls, *xywh)
                        xywh_c4 = xyxy

                im0_000 = im0

                # print kidney
                if c0:
                    label0 = f'{names[0]} '  # {conf_c0:.2f}' remove confidence from image
                    with open(f'{txt_path}.txt', 'a') as f:
                        f.write(('%g ' * len(line0)).rstrip() % line0 + '\n')
                    annotator.box_label(xywh_c0, label0, color=colors(c, True))
                    detected_object = True
                if c2:
                    label2 = f'{names[2]}'  # {conf_c2:.2f}' remove confidence from image
                    with open(f'{txt_path}.txt', 'a') as f:
                        f.write(('%g ' * len(line2)).rstrip() % line2 + '\n')
                    annotator.box_label(xywh_c2, label2, color=colors(c, True))
                    detected_object = True
                if c3:
                    label3 = f'{names[0]}'  # {conf_c3:.2f}'remove confidence from image
                    with open(f'{txt_path}.txt', 'a') as f:
                        f.write(('%g ' * len(line3)).rstrip() % line3 + '\n')
                    annotator.box_label(xywh_c3, label3, color=colors(c, True))
                    detected_object = True
                if c4:
                    label4 = f'{names[2]}'  # {conf_c4:.2f}' remove confidence from image
                    with open(f'{txt_path}.txt', 'a') as f:
                        f.write(('%g ' * len(line4)).rstrip() % line4 + '\n')
                    annotator.box_label(xywh_c4, label=label4, color=colors(c, True))
                    detected_object = True

            # Save results (image with detections)
            im0_000 = annotator.result()
            if save_img:
                if dataset.mode == "image":
                    if detected_object:
                        cv2.imwrite(save_path, im0_000)

    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" \
            if save_txt else ""


def detect_objects(detect_folder, save_conf=True, yolo_weights=ROOT / 'weights/kid_best2908.pt'):
    if os.path.isdir(detect_folder + '/detect'):
        shutil.rmtree(detect_folder + '/detect')
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", nargs="+", type=str, default=yolo_weights, help="model path or triton URL")
    parser.add_argument("--source", type=str, default=detect_folder, help="file/dir/URL/glob/screen/0(webcam)")
    parser.add_argument("--data", type=str, default=None, help="(optional) dataset.yaml path")
    parser.add_argument("--imgsz", "--img", "--img-size", nargs="+", type=int, default=[640], help="inference size h,w")
    parser.add_argument("--conf-thres", type=float, default=0.25, help="confidence threshold")
    parser.add_argument("--iou-thres", type=float, default=0.45, help="NMS IoU threshold")
    parser.add_argument("--max-det", type=int, default=1000, help="maximum detections per image")
    parser.add_argument("--device", default="", help="cuda device, i.e. 0 or 0,1,2,3 or cpu")
    parser.add_argument("--view-img", action="store_true", help="show results")
    parser.add_argument("--save-txt", default=True, help="save results to *.txt")
    parser.add_argument(
        "--save-format",
        type=int,
        default=0,
        help="whether to save boxes coordinates in YOLO format or Pascal-VOC format when save-txt is True, "
             "0 for YOLO "
             "and 1 for Pascal-VOC",
    )
    parser.add_argument("--save-csv", action="store_true", help="save results in CSV format")
    parser.add_argument("--save-conf", default=save_conf, help="save confidences in --save-txt labels")
    parser.add_argument("--save-crop", action="store_true", help="save cropped prediction boxes")
    parser.add_argument("--nosave", action="store_true", help="do not save images/videos")
    parser.add_argument("--classes", nargs="+", type=int, help="filter by class: --classes 0, or --classes 0 2 3")
    parser.add_argument("--agnostic-nms", action="store_true", help="class-agnostic NMS")
    parser.add_argument("--augment", action="store_true", help="augmented inference")
    parser.add_argument("--visualize", action="store_true", help="visualize features")
    parser.add_argument("--update", action="store_true", help="update all models")
    parser.add_argument("--project", default=detect_folder, help="save results to project/name")
    parser.add_argument("--name", default="detect", help="save results to project/name")
    parser.add_argument("--exist-ok", action="store_true", help="existing project/name ok, do not increment")
    parser.add_argument("--line-thickness", default=2, type=int, help="bounding box thickness (pixels)")
    parser.add_argument("--hide-labels", default=False, action="store_true", help="hide labels")
    parser.add_argument("--hide-conf", default=False, action="store_true", help="hide confidences")
    parser.add_argument("--half", action="store_true", help="use FP16 half-precision inference")
    parser.add_argument("--dnn", action="store_true", help="use OpenCV DNN for ONNX inference")
    parser.add_argument("--vid-stride", type=int, default=1, help="video frame-rate stride")

    opt = parser.parse_args()
    opt.imgsz *= 2 if len(opt.imgsz) == 1 else 1  # expand
    run(**vars(opt))
