# BKVisionCamera

## 快速开始

```python
import cv2

from BKVisionCamera import crate_capter

capter = crate_capter(r"demo/HikCA-060-GM.yaml")
with capter as cap:
    frame = cap.getFrame()
    cv2.imshow("frame", frame)
    cv2.waitKey(0)
```

## yaml配置文件

```yaml
# Encoding: utf-8
# Function: 海康CA-060-GM


name: Hikvision #  Hikvision 海康机器人 CCD
configFile: demo/hikCA-060-GM.yaml # 相机配置文件路径


selectType: ip # 选择相机的方式  ip 为IP地址  serial 为串口号 index 为相机索引号
ip: 192.168.3.12

```
