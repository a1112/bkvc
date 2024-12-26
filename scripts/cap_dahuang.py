# -*- coding: utf-8 -*-
import cv2
from tqdm import tqdm
from BKVisionCamera import crate_capter, CaptureModel, HikCamera
capter = crate_capter(r"../demo/Daheng.yaml")  # 创建 采集 模型
tq = tqdm(desc="采集中。。。")
with capter as cap:
    cap: HikCamera
    i = 0
    while i<10000000:
        frame = cap.getFrame()
        i += 1
        tq.update(1)
        print(frame)
        if frame is None:
            break
        cv2.imshow("frame", frame)
        cv2.waitKey(1)