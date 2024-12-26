# -*- coding: utf-8 -*-
from tqdm import tqdm
import cv2
import pytest

from BKVisionCamera import crate_capter, CaptureModel, HikCamera


class TestHikAreaGm:
    def test_hik_area_gm(self):
        # 测试1: 海康 灰度 面扫模块 单相机 非多线程采集
        capter = crate_capter(r"../demo/Daheng.yaml")  # 创建 采集 模型
        tq = tqdm(desc="采集中。。。")
        with capter as cap:
            cap: HikCamera
            i = 0
            while i<1000:
                frame = cap.getFrame()
                i += 1
                tq.update(1)
                if frame is None:
                    break
                # cv2.imshow("frame", frame)
                # cv2.waitKey(1)


pytest.main(["-s", "test_hik_area_gm.py"])
