import numpy as np
import threading
from vispy import app, gloo
from vispy.util.transforms import perspective, translate, rotate
from harvesters.core import Harvester

# 初始化Harvester
h = Harvester()

# 添加GenTL生产者（根据需要调整路径）
h.add_cti_file('BKVisionCamera/d3cancamera/SICK/common/lib/cti/windows_x64/SICKGigEVisionTL.cti')

# 更新设备列表
h.update()

# 连接到第一个可用的相机
ia = h.create_image_acquirer(0)

# 设置全局变量
depth_data = None
intensity_data = None
new_frame_available = False


# 图像采集线程
def acquire_images():
    global depth_data, intensity_data, new_frame_available
    ia.start_acquisition()
    while True:
        buffer = ia.fetch_buffer()
        component0 = buffer.payload.components[0]  # Coord3D_C16
        component1 = buffer.payload.components[1]  # Mono8

        width = component0.width
        height = component0.height

        depth_data = component0.data.reshape(height, width).astype(np.float32)
        depth_data /= np.max(depth_data)

        intensity_data = component1.data.reshape(height, width).astype(np.float32)
        intensity_data /= np.max(intensity_data)

        new_frame_available = True

        buffer.queue()


# 启动图像采集线程
thread = threading.Thread(target=acquire_images, daemon=True)
thread.start()

# 使用Vispy可视化图像数据
# 创建一个Canvas
canvas = app.Canvas(keys='interactive', size=(1024, 600), title='3D图像可视化')

# 顶点着色器
vertex_shader = """
uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
attribute vec3 a_position;
attribute float a_intensity;
varying vec3 v_color;
void main() {
    gl_Position = u_projection * u_view * u_model * vec4(a_position, 1.0);
    v_color = vec3(a_intensity, a_intensity, a_intensity);
}
"""

# 片段着色器
fragment_shader = """
varying vec3 v_color;
void main() {
    gl_FragColor = vec4(v_color, 1.0);
}
"""

# 创建程序并设置着色器
program = gloo.Program(vertex_shader, fragment_shader)

# 设置投影、视图和模型矩阵
program['u_projection'] = perspective(45.0, canvas.size[0] / float(canvas.size[1]), 1.0, 1000.0)
view = translate((0, 0, -500))
model = np.eye(4, dtype=np.float32)


def update_data():
    global new_frame_available
    if new_frame_available:
        height, width = depth_data.shape
        vertices = []
        intensities = []
        for y in range(height):
            for x in range(width):
                z = depth_data[y, x]
                intensity = intensity_data[y, x]
                vertices.append([x, y, z])
                intensities.append(intensity)

        vertices = np.array(vertices, dtype=np.float32)
        intensities = np.array(intensities, dtype=np.float32)

        program['a_position'] = gloo.VertexBuffer(vertices)
        program['a_intensity'] = gloo.VertexBuffer(intensities)

        new_frame_available = False


@canvas.connect
def on_draw(event):
    gloo.clear()
    update_data()
    program['u_view'] = view
    program['u_model'] = model
    program.draw('points')


@canvas.connect
def on_resize(event):
    gloo.set_viewport(0, 0, *event.size)


@canvas.connect
def on_mouse_move(event):
    if event.is_dragging:
        global model
        dx, dy = event.delta
        model = rotate(dx, (0, 1, 0)) @ model
        model = rotate(dy, (1, 0, 0)) @ model
        canvas.update()


canvas.show()
app.run()

# 清理Harvester资源
ia.destroy()
h.reset()