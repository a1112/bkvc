from matplotlib import pyplot as plt
from lib.utils import data_map, extract_color, extract_depth
from lib.IMU import IMUParser
import collections
from matplotlib import animation
from matplotlib.widgets import Button, Slider
import mpl_toolkits.axes_grid1

# based on https://stackoverflow.com/a/46327978


class Player(animation.FuncAnimation):
    def __init__(self, min_acc, max_acc, min_ang, max_ang, frame_list):
        self.frame_list = frame_list
        self.i = 0
        self.min = 0
        self.max = len(self.frame_list) - 1
        self.paused = False
        self.runs = True
        self.forwards = True
        self.acc_x = collections.deque(100*[0], 100)
        self.acc_y = collections.deque(100*[0], 100)
        self.acc_z = collections.deque(100*[0], 100)
        self.ang_x = collections.deque(100*[0], 100)
        self.ang_y = collections.deque(100*[0], 100)
        self.ang_z = collections.deque(100*[0], 100)

        self.fig, axs = plt.subplots(2, 2)

        self.acc_line_x = axs[0, 0].plot(self.acc_x, label="X")[0]
        self.acc_line_y = axs[0, 0].plot(self.acc_y, label="Y")[0]
        self.acc_line_z = axs[0, 0].plot(self.acc_z, label="Z")[0]
        axs[0, 0].legend(loc="upper right")

        axs[0, 0].set_title("Acceleration (m/s²)")
        axs[0, 0].grid(color='gray', linestyle='dashed')
        axs[0, 0].set_ylim([min_acc, max_acc])
        axs[0, 0].set_axisbelow(True)
        axs[1, 0].set_title("Angular Velocity (rad/s)")
        axs[1, 0].grid(color='gray', linestyle='dashed')
        axs[1, 0].set_axisbelow(True)
        axs[1, 0].set_ylim([min_ang, max_ang])
        self.ang_line_x = axs[1, 0].plot(self.ang_x, label="X")[0]
        self.ang_line_y = axs[1, 0].plot(self.ang_y, label="Y")[0]
        self.ang_line_z = axs[1, 0].plot(self.ang_z, label="Z")[0]
        axs[1, 0].legend(loc="upper right")

        axs[0, 1].set_title("Depth Map")
        self.img_depth = axs[0, 1].imshow(self.frame_list[0]["depth"])
        axs[1, 1].set_title("RGB Map")
        self.img_rgb = axs[1, 1].imshow(self.frame_list[0]["rgb"])

        self.setup()
        self.func = self.animate
        self.animate(0)
        animation.FuncAnimation.__init__(self, self.fig, self.update,
                                         frames=self.play(), cache_frame_data=False, interval=20)

    def play(self):
        while self.runs and (self.max - self.min) > 0:
            self.i = self.i+self.forwards-(not self.forwards)
            if self.i > self.min and self.i < self.max:
                yield self.i
            else:
                self.stop()
                yield self.i

    def setup(self, pos=(0.125, 0.92)):
        player_ax = self.fig.add_axes([pos[0], pos[1], 0.64, 0.04])
        divider = mpl_toolkits.axes_grid1.make_axes_locatable(player_ax)
        stop_ax = divider.append_axes("right", size="80%", pad=0.05)
        play_ax = divider.append_axes("right", size="80%", pad=0.05)
        step_forward_ax = divider.append_axes("right", size="100%", pad=0.05)
        slider_ax = divider.append_axes("right", size="500%", pad=0.07)
        self.button_one_back = Button(player_ax, label='$\u29CF$')
        self.button_stop = Button(stop_ax, label='$\u25A0$')
        self.button_forward = Button(play_ax, label='$\u25B6$')
        self.button_one_forward = Button(step_forward_ax, label='$\u29D0$')
        self.button_one_back.on_clicked(self.one_backward)
        self.button_stop.on_clicked(self.stop)
        self.button_forward.on_clicked(self.forward)
        self.button_one_forward.on_clicked(self.one_forward)
        self.slider = Slider(slider_ax, '', self.min,
                             self.max, valinit=self.i, valstep=1)
        self.slider.on_changed(self.set_pos)

    def animate(self, i):
        frame = self.frame_list[i]
        for x in frame["acc_x"]:
            self.acc_x.append(x)
        for y in frame["acc_y"]:
            self.acc_y.append(y)
        for z in frame["acc_z"]:
            self.acc_z.append(z)

        for x in frame["ang_x"]:
            self.ang_x.append(x)
        for y in frame["ang_y"]:
            self.ang_y.append(y)
        for z in frame["ang_z"]:
            self.ang_z.append(z)

        self.acc_line_x.set_data(range(100), self.acc_x)
        self.acc_line_y.set_data(range(100), self.acc_y)
        self.acc_line_z.set_data(range(100), self.acc_z)

        self.ang_line_x.set_data(range(100), self.ang_x)
        self.ang_line_y.set_data(range(100), self.ang_y)
        self.ang_line_z.set_data(range(100), self.ang_z)

        self.img_depth.set(data=frame["depth"])
        self.img_rgb.set(data=frame["rgb"])

    def update(self, i):
        self.slider.set_val(i)

    def set_pos(self, i):
        if i < self.max:
            self.i = int(self.slider.val)
            self.animate(self.i)

    def stop(self, event=None):
        self.runs = False
        self.event_source.stop()

    def start(self):
        self.runs = True
        self.event_source.start()

    def forward(self, event=None):
        self.forwards = True
        self.start()

    def one_forward(self, event=None):
        self.forwards = True
        self.one_step()

    def one_backward(self, event=None):
        self.forwards = False
        self.one_step()

    def one_step(self):
        if (self.max - self.min) > 0:
            if self.i > self.min and self.i < self.max:
                self.i = self.i+self.forwards-(not self.forwards)
            elif self.i == self.min and self.forwards:
                self.i += 1
            elif self.i == self.max and not self.forwards:
                self.i -= 1
            self.animate(self.i)
            self.slider.set_val(self.i)
            self.fig.canvas.draw_idle()
