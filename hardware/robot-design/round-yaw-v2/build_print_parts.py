"""EffMeet2 圆润转头版 · 打印件建模 + 渲染（布局 A / 微雪主板 / PLA Matte）

用法：
  blender --background --python build_print_parts.py

历史草案提示：当前模型与安装入口为 revision-20261011-nomi-layoutA/README.md。
本脚本不是当前生成源，不应直接用其STL打印整机；已有文件仅供追溯。

输出：
  stl/*.stl            历史草案网格（1:1 mm，未经过制造／装配放行）
  renders/*.png        整机渲染图（三视角 + 爆炸）

依据：round-yaw-v2/parameters.json、MODELING_BRIEF.md（美学不变量）、PRINT_PLAN.md
状态：可逆封装布局级 blockout，不是制造放行、不是实机验收。
"""

import bpy
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT_STL = os.path.join(HERE, "stl")
OUT_PNG = os.path.join(HERE, "renders")
os.makedirs(OUT_STL, exist_ok=True)
os.makedirs(OUT_PNG, exist_ok=True)

# ---------------------------------------------------------------- 几何参数（parameters.json）
ENV_W, ENV_D, ENV_H = 180.0, 164.0, 222.0
HEAD_W, HEAD_D, HEAD_H = 150.0, 128.0, 144.0
HEAD_C = (0.0, 0.0, 150.0)
BASE_W, BASE_D, BASE_H = 180.0, 164.0, 76.0
BASE_TOP = 78.0
FOOT_H = 2.0
WALL = 2.4
NECK_OD, NECK_ID = 46.0, 22.0
NECK_GAP = 14.0
FACE_D = 106.0
LCD_W, LCD_H = 49.0, 37.0
BEARING_OD, BEARING_ID, BEARING_W = 42.0, 30.0, 7.0
SERVO_W, SERVO_D, SERVO_H = 22.8, 12.2, 28.5


# ---------------------------------------------------------------- 基础工具
def clean():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for b in list(bpy.data.meshes):
        bpy.data.meshes.remove(b)


def cube(name, sx, sy, sz, loc=(0, 0, 0), bevel=0.0, segs=4):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        m = o.modifiers.new("bev", "BEVEL")
        m.width = bevel
        m.segments = segs
        m.limit_method = "ANGLE"
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)
    return o


def cyl(name, r, depth, loc=(0, 0, 0), verts=64, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, location=loc, vertices=verts, rotation=rot
    )
    o = bpy.context.object
    o.name = name
    return o


def sphere(name, r, loc=(0, 0, 0), segs=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=r, location=loc, segments=segs, ring_count=rings
    )
    o = bpy.context.object
    o.name = name
    return o


def cut(target, cutter):
    m = target.modifiers.new("bool", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def intersect(target, cutter):
    m = target.modifiers.new("bool", "BOOLEAN")
    m.operation = "INTERSECT"
    m.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def smooth(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    for e in obj.data.edges:
        e.use_edge_sharp = True


def export_stl(obj, filename):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT_STL, filename), global_scale=1.0)
    print("STL", filename)


# ---------------------------------------------------------------- 材料
def make_mats():
    mats = {}

    def mk(name, rgb, rough=0.72, metal=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = next(
            (n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"),
            None,
        )
        if bsdf is None:
            bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        mats[name] = m
        return m

    mk("body_gray", (0.78, 0.79, 0.81), 0.74)      # PLA Matte 灰机身
    mk("panel_black", (0.018, 0.018, 0.022), 0.42)  # 炭黑面板
    mk("lcd_dark", (0.012, 0.012, 0.015), 0.22)    # 屏内黑
    mk("eye_warm", (0.96, 0.90, 0.80), 0.35)       # 暖白眼睛
    mk("coral", (0.94, 0.32, 0.18), 0.45)          # 珊瑚状态短划
    mk("floor", (0.55, 0.55, 0.56), 0.92)
    return mats


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


# ---------------------------------------------------------------- 打印件建模
def part_head_shell():
    """头壳：近球形略压扁，正面 Ø108 圆柱沉口袋（深 14）供黑面板嵌入。"""
    o = sphere("C01a_head_shell", 1.0, HEAD_C)
    o.scale = (HEAD_W / 2, HEAD_D / 2, HEAD_H / 2)
    bpy.ops.object.transform_apply(scale=True)
    cut(o, cube("c", 400, 400, 400, (0, 0, 92 - 200)))
    # 面板沉口袋：Ø108、沿 -Y 向内 14mm（面板嵌入后齐平/微沉）
    face_y = -HEAD_D / 2 + 6
    cut(o, cyl("pocket", 54.0, 14.0, (0, face_y + 6.0, HEAD_C[2] + 6), rot=(math.pi / 2, 0, 0)))
    # 内腔（壁厚 2.4）
    inner = sphere("i", 1.0, HEAD_C)
    inner.scale = ((HEAD_W / 2) - WALL, (HEAD_D / 2) - WALL, (HEAD_H / 2) - WALL)
    bpy.ops.object.transform_apply(scale=True)
    cut(inner, cube("c2", 400, 400, 400, (0, 0, 92 - 200 - WALL)))
    cut(o, inner)
    smooth(o)
    return o


def part_base_cup():
    """底座杯体：软圆鹅卵石，底面平。"""
    o = cube("C01b_base_cup", BASE_W, BASE_D, BASE_H, (0, 0, 2 + BASE_H / 2), bevel=22, segs=10)
    inner = cube("i", BASE_W - 2 * WALL, BASE_D - 2 * WALL, BASE_H, (0, 0, 2 + BASE_H / 2 + WALL), bevel=11, segs=6)
    cut(o, inner)
    # 底面开工艺口（不封死）
    cut(o, cube("bot", 60, 60, 30, (0, 0, 2)))
    # 转轴孔 Ø48
    cut(o, cyl("yaw", 24.0, 60, (0, 0, 60)))
    # 扬声器声槽 3 条（下前）
    for i, x in enumerate((-34, 0, 34)):
        cut(o, cube("slot%d" % i, 26, 8, 7, (x, -BASE_D / 2 + 16, 20)))
    # 双麦声孔（上缘，固定不随头转）
    for x in (-46, 46):
        cut(o, cyl("mic", 1.6, 40, (x, -BASE_D / 2 + 20, 70), verts=24, rot=(math.pi / 2, 0, 0)))
    # Type-C 浅凹槽（后侧）
    cut(o, cube("usbc", 12, 18, 9, (0, BASE_D / 2 - 4, 26)))
    smooth(o)
    return o


def part_base_lid():
    """底座上盖：可拆接缝 + 转轴孔。"""
    o = cyl("C01c_base_lid", 1.0, 6)
    o.scale = (BASE_W / 2 - 4, BASE_D / 2 - 4, 1)
    bpy.ops.object.transform_apply(scale=True)
    o.location = (0, 0, 68)
    cut(o, cyl("yaw", 24.0, 40, (0, 0, 68)))
    smooth(o)
    return o


def part_face_panel():
    """圆形黑面板：Ø106 × 3 平板，嵌入头壳沉口袋；中央矩形 LCD 窗贯通。"""
    face_y = -HEAD_D / 2 + 6
    o = cyl("C02_face_panel", 53.0, 3.0, (0, face_y + 3.5, HEAD_C[2] + 6), rot=(math.pi / 2, 0, 0))
    cut(o, cube("win", LCD_W, 20, LCD_H, (0, face_y + 3.5, HEAD_C[2] + 1), bevel=3, segs=3))
    cut(o, cyl("cam", 5.5, 20, (0, face_y + 3.5, HEAD_C[2] + 30), rot=(math.pi / 2, 0, 0)))
    cut(o, cube("shut", 15, 20, 9, (0, face_y + 3.5, HEAD_C[2] + 30)))
    smooth(o)
    return o


def part_neck():
    """短颈外观件：46 轴径 + 裙边，高 14 = 头-底座真实间距。"""
    o = cyl("C03_neck", NECK_OD / 2 + 6, NECK_GAP + 10, (0, 0, 85))
    cut(o, cyl("bore", NECK_OD / 2, 60, (0, 0, 85)))
    smooth(o)
    return o


def part_bearing_seat():
    """轴承座（分体夹紧式，PLA 不做强过盈）。"""
    o = cube("M04_bearing_seat", 62, 62, BEARING_W + 6, (0, 0, (BEARING_W + 6) / 2), bevel=6, segs=4)
    cut(o, cyl("bore", BEARING_OD / 2 + 0.15, 40, (0, 0, (BEARING_W + 6) / 2)))
    # 分体开口 + 两颗 M3 抱箍孔
    cut(o, cube("split", 8, 80, 40, (31, 0, (BEARING_W + 6) / 2)))
    for y in (-22, 22):
        cut(o, cyl("m3", 1.7, 40, (24, y, (BEARING_W + 6) / 2), verts=24, rot=(0, math.pi / 2, 0)))
    smooth(o)
    return o


def part_servo_mount():
    """舵机架：MG90S 口袋 + 固定耳孔。"""
    o = cube("M04_servo_mount", 40, 30, 34, (0, 0, 17), bevel=3, segs=3)
    cut(o, cube("pocket", SERVO_W, SERVO_D + 0.3, SERVO_H + 4, (0, 0, 19)))
    for y in (-17, 17):
        cut(o, cyl("ear", 1.7, 40, (0, y, 30), verts=24))
    smooth(o)
    return o


def part_hub():
    """轮毂/连接盘：接轴承与头部。"""
    o = cyl("M04_hub", 34, 10, (0, 0, 5))
    cut(o, cyl("bore", BEARING_ID / 2, 40, (0, 0, 5)))
    for i in range(4):
        a = math.pi / 2 * i + math.pi / 4
        cut(o, cyl("s%d" % i, 1.8, 40, (22 * math.cos(a), 22 * math.sin(a), 5), verts=20))
    smooth(o)
    return o


def part_pulley():
    """同齿数带轮（简化：外齿轮廓 + 中央孔）。"""
    o = cyl("M03_pulley", 14, 7, (0, 0, 3.5), verts=48)
    for i in range(20):
        a = 2 * math.pi * i / 20
        cut(o, cube("t%d" % i, 2.2, 2.2, 20, (14 * math.cos(a), 14 * math.sin(a), 3.5)))
    cut(o, cyl("bore", 3.0, 40, (0, 0, 3.5)))
    smooth(o)
    return o


def part_button_cap():
    o = cyl("C05_button_cap", 6, 4, (0, 0, 2), verts=32)
    cut(o, cyl("pilot", 3.2, 20, (0, 0, 1)))
    smooth(o)
    return o


def part_slider():
    o = cube("C04_slider", 22, 3.0, 13, (0, 0, 1.5), bevel=1.2, segs=3)
    return o


def part_cable_clip():
    o = cyl("M07_cable_clip", 6, 6, (0, 0, 3), verts=32)
    cut(o, cyl("bore", 3.6, 20, (0, 0, 3)))
    cut(o, cube("mouth", 8, 20, 20, (6, 0, 3)))
    smooth(o)
    return o


BUILDERS = [
    ("01_C01a_head_shell.stl", part_head_shell),
    ("02_C01b_base_cup.stl", part_base_cup),
    ("03_C01c_base_lid.stl", part_base_lid),
    ("04_C02_face_panel.stl", part_face_panel),
    ("05_C03_neck.stl", part_neck),
    ("06_bearing_seat_x2.stl", part_bearing_seat),
    ("07_servo_mount.stl", part_servo_mount),
    ("08_hub.stl", part_hub),
    ("09_pulley_x2.stl", part_pulley),
    ("10_button_cap.stl", part_button_cap),
    ("11_slider.stl", part_slider),
    ("12_cable_clip.stl", part_cable_clip),
]


# ---------------------------------------------------------------- 渲染
def setup_scene(mats):
    clean()
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = eng
            break
        except Exception:
            continue
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.film_transparent = False

    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.58, 0.58, 0.60, 1)
    bg.inputs[1].default_value = 1.0

    # 地面
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "floor"
    assign(floor, mats["floor"])

    # 三点光
    def area(name, loc, energy, size, rot):
        bpy.ops.object.light_add(type="AREA", location=loc, rotation=rot)
        L = bpy.context.object
        L.name = name
        L.data.energy = energy
        L.data.size = size
        return L

    area("key", (300, -380, 420), 5200, 300, (math.radians(48), 0, math.radians(36)))
    area("fill", (-360, -240, 220), 700, 380, (math.radians(66), 0, math.radians(-58)))
    area("rim", (40, 380, 340), 3200, 200, (math.radians(-56), 0, math.radians(6)))


def build_robot(mats):
    """装配态：头部 + 面板 + 短颈 + 底座 + 上盖。"""
    objs = {}
    head = part_head_shell(); assign(head, mats["body_gray"]); objs["head"] = head
    panel = build_face_visual(mats); objs["panel"] = panel
    neck = part_neck(); assign(neck, mats["panel_black"]); objs["neck"] = neck
    base = part_base_cup(); assign(base, mats["body_gray"]); objs["base"] = base
    lid = part_base_lid(); assign(lid, mats["body_gray"]); objs["lid"] = lid

    # 屏内黑 + 眼睛（放在 LCD 窗后）
    # 珊瑚状态短划（底座前部）
    dash = cube("status", 16, 1.2, 2.2, (0, -BASE_D / 2 + 2.2, 34))
    assign(dash, mats["coral"])
    return objs


def build_face_visual(mats):
    """渲染专用面部：三层全部放在面板**前方**（朝相机，-Y），物理上保证可见，零布尔。
    层序（相机在 -Y）：眼 y≈-59.5 → 屏 y≈-58.2 → 面板 y≈-56.5"""
    face_y = -HEAD_D / 2 + 6          # -58
    panel = cyl("vis_panel", 53.0, 2.5, (0, face_y + 1.5, HEAD_C[2] + 6), rot=(math.pi / 2, 0, 0))
    assign(panel, mats["panel_black"]); smooth(panel)
    scr = cube("vis_screen", 50.0, 1.2, 38.0, (0, face_y - 0.2, HEAD_C[2] + 1), bevel=5, segs=5)
    assign(scr, mats["lcd_dark"])
    for x in (-13, 13):
        e = sphere("vis_eye", 9.0, (x, face_y - 1.6, HEAD_C[2] - 3))
        e.scale = (1.0, 0.30, 0.34)
        bpy.ops.object.transform_apply(scale=True)
        assign(e, mats["eye_warm"]); smooth(e)
    cam = cyl("vis_cam", 4.5, 1.0, (0, face_y - 0.6, HEAD_C[2] + 30), rot=(math.pi / 2, 0, 0))
    assign(cam, mats["lcd_dark"]); smooth(cam)
    return panel


def render_views(prefix):
    scene = bpy.context.scene

    def cam(name, loc, lens, target=(0, 0, 112)):
        bpy.ops.object.camera_add(location=loc)
        c = bpy.context.object
        c.name = name
        c.data.lens = lens
        # 朝目标
        d = (target[0] - loc[0], target[1] - loc[1], target[2] - loc[2])
        import mathutils
        c.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
        return c

    shots = [
        ("front34", (360, -560, 300), 52),
        ("front", (0, -680, 150), 52),
        ("side", (600, -140, 165), 52),
    ]
    for key, loc, lens in shots:
        c = cam("cam_" + key, loc, lens)
        scene.camera = c
        scene.render.filepath = os.path.join(OUT_PNG, "%s_%s.png" % (prefix, key))
        bpy.ops.render.render(write_still=True)
        print("RENDER", key)


# ---------------------------------------------------------------- 主流程
if __name__ == "__main__":
    mats = make_mats()

    # 1) 逐件出 STL
    clean()
    for fname, fn in BUILDERS:
        clean()
        o = fn()
        export_stl(o, fname)

    # 2) 装配态渲染
    setup_scene(mats)
    build_robot(mats)
    render_views("v3_layoutA")

    print("DONE ->", OUT_STL, "|", OUT_PNG)
