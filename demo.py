from tqdm import tqdm
import cv2

from BKVisionCamera import crate_capter, HikCamera

capter = crate_capter(r"demo/Area_L_D.yaml")  # 创建 采集 :海康 灰度 面扫模块 单相机 非多线程采集
with capter as cap:
    tq = tqdm(desc=f"{capter.camera_info.ip} w:{capter.sdk.width} h:{capter.sdk.height} 采集中...")
    cap: HikCamera
    while True:
        frame = cap.getFrame()
        if frame is None:
            continue
        tq.update(1)
        cv2.imshow("frame", frame)
        cv2.waitKey(1)

