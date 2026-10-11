"""EffMeet2 配合样片生成脚本（Blender 无头运行）

用法：
  blender --background --python generate_fit_coupons.py

输出：fit-coupons/*.stl（1:1 单位 mm，直接切片）
用途：PETG/PLA 配合验证，验「装不装得进、公差带哪档合适」，不验最终材料强度。
尺寸来源：BOM §12.2（M02 轴承 6806 = 30×42×7；M01 舵机 MG90S 本体 22.8×12.2×28.5）
"""

import bpy
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
os.makedirs(OUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes):
        bpy.data.meshes.remove(block)


def box(name, sx, sy, sz, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    # size=1 的立方体本身就是 1 单位，scale 直接取目标尺寸
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    return o


def cyl(name, radius, depth, loc, verts=64):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=loc, vertices=verts
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


def export(obj, filename):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT_DIR, filename)
    bpy.ops.wm.stl_export(filepath=path, global_scale=1.0)
    print("WROTE", path)


# ---------------------------------------------------------------- 公差带取值
# 打印件内孔通常比名义值小 0.1~0.4（材料收缩 + 挤出过挤），
# 所以做一串递增孔径，上机试装后挑一档作为设计值。
BEARING_OD = 42.0          # 6806 外圈外径
BEARING_ID = 30.0          # 6806 内圈内径
BEARING_W = 7.0            # 6806 宽度
SHAFT_OD = 46.0            # 转轴名义外径（prompt.txt）
SERVO_W, SERVO_D, SERVO_H = 22.8, 12.2, 28.5   # MG90S 本体


def coupon_bearing_od():
    """轴承外圈压配样片：4 档 Ø42 孔，找抱箍/压配合适的那一档。"""
    clear_scene()
    holes = [42.0, 42.2, 42.4, 42.6]
    pitch = 48.0
    plate = box("bearing_od_plate",
                pitch * (len(holes) - 1) + 44.0,
                52.0,
                BEARING_W,
                (0, 0, BEARING_W / 2.0))
    for i, d in enumerate(holes):
        x = (i - (len(holes) - 1) / 2.0) * pitch
        cut(plate, cyl("h", d / 2.0, BEARING_W * 3, (x, 0, BEARING_W / 2.0)))
    export(plate, "01_bearing_OD_ladder.stl")


def coupon_bearing_id():
    """轴承内圈/轴配合样片：3 档 Ø30 孔 + 1 档 Ø46 轴径校核。"""
    clear_scene()
    bores = [30.0, 30.1, 30.2]
    pitch = 52.0
    plate = box("bearing_id_plate",
                pitch * (len(bores) - 1) + 52.0 + pitch,
                52.0,
                BEARING_W,
                (0, 0, BEARING_W / 2.0))
    for i, d in enumerate(bores):
        x = (i - (len(bores) + 1) / 2.0) * pitch
        cut(plate, cyl("h", d / 2.0, BEARING_W * 3, (x, 0, BEARING_W / 2.0)))
    x_shaft = (len(bores) + 1) / 2.0 * pitch
    cut(plate, cyl("shaft", SHAFT_OD / 2.0, BEARING_W * 3,
                   (x_shaft, 0, BEARING_W / 2.0)))
    export(plate, "02_bearing_ID_and_shaft_ladder.stl")


def coupon_servo_wall():
    """舵机口袋 + 壁厚/孔质量样片。"""
    clear_scene()
    plate = box("servo_wall_plate", 90.0, 70.0, 6.0, (0, 0, 3.0))

    # 左半：MG90S 口袋（开口朝 +Z，深度 5mm）
    pocket = box("pocket", SERVO_W, SERVO_D, 5.0, (-22.0, 0, 5.5))
    cut(plate, pocket)
    # 舵机固定耳孔（简化为两条通孔，位置按实测再调）
    for dy in (-16.0, 16.0):
        cut(plate, cyl("ear", 1.6, 20, (-22.0, dy, 3.0), verts=32))

    # 右半：壁厚台阶 + 孔质量阶梯
    for i, d in enumerate([2.0, 3.0, 4.0, 5.0, 6.0]):
        cut(plate, cyl("hole", d / 2.0, 20,
                       (10.0 + i * 14.0, 18.0, 3.0), verts=48))
    # 2.4mm 名义壁厚的窄梁（看层纹与强度观感）
    cut(plate, box("slot", 60.0, 3.0, 20.0, (20.0, -18.0, 3.0)))

    export(plate, "03_servo_pocket_and_wall.stl")


def coupon_shortneck():
    """短颈接收面样片：14mm 头-底座间距 + 46mm 轴外径，验证裙边诚实间隙。"""
    clear_scene()
    base = cyl("collar", SHAFT_OD / 2.0 + 6.0, 14.0, (0, 0, 7.0))
    cut(base, cyl("bore", SHAFT_OD / 2.0, 40, (0, 0, 7.0)))
    export(base, "04_shortneck_clearance.stl")


if __name__ == "__main__":
    coupon_bearing_od()
    coupon_bearing_id()
    coupon_servo_wall()
    coupon_shortneck()
    print("ALL COUPONS DONE ->", OUT_DIR)
