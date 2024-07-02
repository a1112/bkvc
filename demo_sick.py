import harvesters
import numpy as np
from tqdm import tqdm
import cv2

from BKVisionCamera import crate_capter, SickCamera
from vispy import app, gloo
from vispy.util.transforms import perspective, translate, rotate
capter = crate_capter(r"demo/SickCA-3D.yaml")  # 创建 采集 :海康 灰度 面扫模块 单相机 非多线程采集
with capter as cap:
    tq = tqdm(desc=f"{capter.camera_info.ip} w:{capter.sdk.width} h:{capter.sdk.height} 采集中...")
    cap: SickCamera
    while True:
        # frame = cap.getFrame()[0]
        # tq.update(1)
        # print(frame.sum())
        # cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
        # cv2.imshow("frame", frame)
        # cv2.waitKey(1)
        buffer = cap.getFrame().__next__()
        buffer: harvesters.core.Buffer
        component = buffer.payload.components[0]
        width = component.width
        height = component.height
        print(component.data.sum())
        data = component.data.reshape(1024, 2560)
        data_normalized = data.astype(np.float32) / np.max(data)
        canvas = app.Canvas(keys='interactive', size=(800, 600), title='3D Image Visualization')

        # Vertex shader
        vertex_shader = """
        uniform mat4 u_model;
        uniform mat4 u_view;
        uniform mat4 u_projection;
        attribute vec3 a_position;
        attribute float a_depth;
        varying vec3 v_color;
        void main() {
            gl_Position = u_projection * u_view * u_model * vec4(a_position, 1.0);
            v_color = vec3(a_depth, a_depth, a_depth);
        }
        """

        # Fragment shader
        fragment_shader = """
        varying vec3 v_color;
        void main() {
            gl_FragColor = vec4(v_color, 1.0);
        }
        """

        # Create program and set shaders
        program = gloo.Program(vertex_shader, fragment_shader)

        # Generate 3D vertices and depth data from image
        vertices = []
        depths = []
        for y in range(height):
            for x in range(width):
                z = data_normalized[y, x]
                vertices.append([x, y, z])
                depths.append(z)

        vertices = np.array(vertices, dtype=np.float32)
        depths = np.array(depths, dtype=np.float32)

        # Bind vertices and depth data to the program
        program['a_position'] = gloo.VertexBuffer(vertices)
        program['a_depth'] = gloo.VertexBuffer(depths)

        # Set projection, view, and model matrices
        program['u_projection'] = perspective(45.0, canvas.size[0] / float(canvas.size[1]), 1.0, 1000.0)
        view = translate((0, 0, -500))
        model = np.eye(4, dtype=np.float32)


        @canvas.connect
        def on_draw(event):
            gloo.clear()
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
        # Cleanup Harvester resources

# with capter as cap:
#     tq = tqdm(desc=f"{capter.camera_info.ip} w:{capter.sdk.width} h:{capter.sdk.height} 采集中...")
#     cap: SickCamera
#     while True:
#         frame = cap.getFrame()
#         # cap.setExposureTime(100)9
#         tq.update(1)
#         cv2.imshow("frame", frame)
#         cv2.waitKey(1)
