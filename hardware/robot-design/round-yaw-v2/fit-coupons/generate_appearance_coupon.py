"""外观／材料样片（PLA Matte 观感与工艺基线）——单件，一盘打完

上机验证：哑光观感 · 层纹 · 曲面质量 · 45°支撑痕 · 2.4mm薄壁 · 孔径 · 圆角
运行：blender --background --python generate_appearance_coupon.py

坐标约定：基板底面 = z0，所有件从 z0 向上生长，全部落在打印平台上。
"""
import bpy, math, os

OUT = os.path.dirname(os.path.abspath(__file__))
Z0 = 0.0          # 打印平台
BASE_H = 4.0      # 基板厚
TOP = Z0 + BASE_H # 基板顶面 = 4

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for b in list(bpy.data.meshes): bpy.data.meshes.remove(b)

def box(n, sx, sy, sz, loc, bevel=0.0, segs=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = n
    o.scale = (sx, sy, sz); bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        m = o.modifiers.new("b","BEVEL"); m.width=bevel; m.segments=segs
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=m.name)
    return o

def cyl(n,r,d,loc,verts=64,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r,depth=d,location=loc,vertices=verts,rotation=rot)
    o=bpy.context.object; o.name=n; return o

def sph(n,r,loc):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r,location=loc,segments=72,ring_count=36)
    o=bpy.context.object; o.name=n; return o

def cut(t,c):
    m=t.modifiers.new("bool","BOOLEAN"); m.operation='DIFFERENCE'; m.object=c
    bpy.context.view_layer.objects.active=t; bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(c,do_unlink=True)

def join(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o=bpy.context.object; o.name=name
    bpy.ops.object.shade_smooth()
    return o

clear()
parts=[]

# ---- 基板 140 × 90 × 4，底面在 z0 ----
base = box("base", 140, 90, BASE_H, (0, 0, Z0 + BASE_H/2))
# 孔阶梯 Ø2/3/4/5/6（前缘一排）
for i,d in enumerate([2.0,3.0,4.0,5.0,6.0]):
    cut(base, cyl("h", d/2.0, BASE_H*3, (-46+i*11, -34, Z0 + BASE_H/2), verts=48))
parts.append(base)

# ---- ① 球冠：R=70（贴近头壳曲率），冠顶高出基板顶 12mm ----
R = 70.0
CAP_H = 12.0                      # 高出基板顶的量
top_z = TOP + CAP_H               # 冠顶 z=16
cz = top_z - R                    # 球心 z = 16-70 = -54
dome = sph("dome", R, (-36, 10, cz))
cut(dome, box("k0", 500,500,500, (0,0, cz - 250)))            # 只留球心以上
cut(dome, box("k1", 500,500,500, (-36-44-250, 10, 0)))        # 裁到 Ø88 内
cut(dome, box("k2", 500,500,500, (-36+44+250, 10, 0)))
cut(dome, box("k3", 500,500,500, (-36, 10-44-250, 0)))
cut(dome, box("k4", 500,500,500, (-36, 10+44+250, 0)))
cut(dome, box("klow", 500,500,500, (-36, 10, TOP - 2 - 250)))  # 底面切到 z=2（与基板重叠2mm，保证实体相连）
parts.append(dome)

# ---- ② 45° 悬垂臂：立柱 + 斜出段 ----
post = box("post", 10, 10, 30, (36, 14, TOP + 15))
arm  = box("arm", 4, 8, 26, (0, 0, 0))
bpy.context.view_layer.objects.active = arm
arm.rotation_euler = (0, math.radians(45), 0)
bpy.ops.object.transform_apply(rotation=True)
arm.location = (36 + 9.2, 14, TOP + 30 + 9.2)
parts += [post, arm]

# ---- ③ 2.4mm 薄壁 ----
wall = box("wall24", 38, 2.4, 26, (8, 32, TOP + 13), bevel=0.8, segs=3)
parts.append(wall)

# ---- ④ 圆角块 R4 ----
edge = box("edge", 26, 18, 12, (40, -26, TOP + 6), bevel=4, segs=6)
parts.append(edge)

# ---- ⑤ 竖直平面（层线密度） ----
flat = box("flat", 24, 16, 22, (-16, 34, TOP + 11))
parts.append(flat)

o = join(parts, "APPEARANCE_COUPON")
xs=[(o.matrix_world@v.co) for v in o.data.vertices]
def r(i): return (round(min(v[i] for v in xs),1), round(max(v[i] for v in xs),1))
print("BBOX X",r(0),"Y",r(1),"Z",r(2))
bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
bpy.context.view_layer.objects.active = o
p = os.path.join(OUT, "A0_appearance_coupon.stl")
bpy.ops.wm.stl_export(filepath=p, global_scale=1.0, export_selected_objects=True)
print("WROTE", p, "verts", len(o.data.vertices))
