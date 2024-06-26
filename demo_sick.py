from tqdm import tqdm
import cv2

from BKVisionCamera import crate_capter, SickCamera

capter = crate_capter(r"demo/SickCA-3D.yaml")  # 创建 采集 :海康 灰度 面扫模块 单相机 非多线程采集
with capter as cap:
    tq = tqdm(desc=f"{capter.camera_info.ip} w:{capter.sdk.width} h:{capter.sdk.height} 采集中...")
    cap: SickCamera
    frame = cap.getFrame()
    tq.update(1)
    cv2.imshow("frame", frame)
    cv2.waitKey(1)

with capter as cap:
    tq = tqdm(desc=f"{capter.camera_info.ip} w:{capter.sdk.width} h:{capter.sdk.height} 采集中...")
    cap: SickCamera
    while True:
        frame = cap.getFrame()
        # cap.setExposureTime(100)
        tq.update(1)
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
