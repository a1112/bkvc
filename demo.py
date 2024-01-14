import cv2

from BKVisionCamera import crate_capter
capter = crate_capter(r"demo/HikCA-060-GM.yaml")
with capter as cap:
    frame = cap.getFrame()
    cv2.imshow("frame", frame)
    cv2.waitKey(0)