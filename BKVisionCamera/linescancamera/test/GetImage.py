from pypylon import pylon
import time
from tqdm import tqdm
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()

# demonstrate some feature access
new_width = camera.Width.GetValue() - camera.Width.GetInc()
if new_width >= camera.Width.GetMin():
    camera.Width.SetValue(new_width)

numberOfImagesToGrab = 10000000
camera.StartGrabbingMax(numberOfImagesToGrab)


FPS = 0
startTime=time.time()
ImageCount=0


pbar = tqdm(desc="Basler 相机 count",total=ImageCount)

while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
    if grabResult.GrabSucceeded():
        ImageCount += 1
        pbar.update()
        # Access the image data.
        # print("SizeX: ", grabResult.Width)
        # print("SizeY: ", grabResult.Height)
        # img = grabResult.Array
        # print("Gray value of first pixel: ", img[0, 0])

    grabResult.Release()
camera.Close()