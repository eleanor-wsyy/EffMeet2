# 生成 P03 对开抱轴式两半（路径 2）：
#   1) 导入 P03 STL；2) 量齿相位，把剖分面放到最近齿隙（约 30°，避开 0° 顶丝通道）；
#   3) 布尔切两半（带封面）；4) 每半加 2 个跨缝螺耳 + 孔（A 侧 Ø2.2 过孔，B 侧 Ø1.5 自攻底孔）；
#   5) 导出 P03_SPLIT_A/B.stl，并做流形/体积自检。
# 运行："D:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python tools/build_p03_split.py
import bpy, bmesh, math, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
SRC = os.path.join(ROOT, "candidate-stl", "P03_DRIVEN_64T_UNVERIFIED.stl")
OUT = os.path.join(ROOT, "p03_fix")
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.wm.stl_import(filepath=SRC)
except Exception:
    bpy.ops.import_mesh.stl(filepath=SRC)
src = bpy.context.selected_objects[0]
src.name = "P03_SRC"

# ---- 基准量测 ----
mw = src.matrix_world
bb = [mw @ Vector(c) for c in src.bound_box]
cx = (min(v.x for v in bb) + max(v.x for v in bb)) / 2
cy = (min(v.y for v in bb) + max(v.y for v in bb)) / 2
z0, z1 = min(v.z for v in bb), max(v.z for v in bb)
H = z1 - z0
print("P03 bbox center", round(cx, 2), round(cy, 2), "z", round(z0, 2), round(z1, 2))

dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(src, dg)

def outer_r(theta_deg, z):
    t = math.radians(theta_deg)
    o = Vector((cx + 40 * math.cos(t), cy + 40 * math.sin(t), z))
    d = Vector((-math.cos(t), -math.sin(t), 0))
    hit = bvh.ray_cast(o, d)
    return None if hit[0] is None else math.hypot(hit[0].x - cx, hit[0].y - cy)

mid_z = z0 + H / 2
prof = []
for a in [x * 0.5 for x in range(40, 81)]:  # 20°..40°
    r = outer_r(a, mid_z)
    if r: prof.append((a, round(r, 2)))
print("20-40deg outer profile:", prof[:80])
# 齿隙=半径最小处；找 30° 附近最接近齿隙的角度
gap = min(prof, key=lambda t: t[1]) if prof else (30.0, 0)
# 优先在 25°–35° 里找齿隙（离 0° 顶丝通道和 D 平边缘都留足距离）
prof_pref = [t for t in prof if 25 <= t[0] <= 35] or prof
if prof_pref:
    gap = min(prof_pref, key=lambda t: t[1])
phi = gap[0]
print("chosen seam angle:", phi, "r=", gap[1])

u = Vector((math.cos(math.radians(phi)), math.sin(math.radians(phi)), 0))
v = Vector((-math.sin(math.radians(phi)), math.cos(math.radians(phi)), 0))
zc = Vector((0, 0, 1))

def add_box(name, u0, v0, zc0, du, dv, dz):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    R = Matrix(((u.x, v.x, 0, 0), (u.y, v.y, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    S = Matrix.Diagonal((du, dv, dz, 1))
    T = Matrix.Translation(Vector((cx, cy, 0)) + u * u0 + v * v0 + Vector((0, 0, zc0)))
    o.matrix_world = T @ R @ S
    return o

def add_cyl(name, u0, v0, zc0, r, depth):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=depth, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    R = Matrix(((u.x, 0, v.x, 0), (u.y, 0, v.y, 0), (0, 1, 0, 0), (0, 0, 0, 1)))  # local z -> v
    T = Matrix.Translation(Vector((cx, cy, 0)) + u * u0 + v * v0 + Vector((0, 0, zc0)))
    o.matrix_world = T @ R
    return o

def boolean(target, tool, op):
    bpy.context.view_layer.objects.active = target
    m = target.modifiers.new("bool", 'BOOLEAN')
    m.object = tool
    m.operation = op
    m.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)

def duplicate(o, name):
    d = o.copy()
    d.data = o.data.copy()
    d.name = name
    bpy.context.collection.objects.link(d)
    return d

# ---- 切两半 ----
halfA = duplicate(src, "P03_SPLIT_A")   # v > 0
halfB = duplicate(src, "P03_SPLIT_B")   # v < 0
cutA = add_box("cutA", 0, 60.0, z0 + H / 2, 200, 120, H * 4)   # 盖在 v>0 侧
cutB = add_box("cutB", 0, -60.0, z0 + H / 2, 200, 120, H * 4)
boolean(halfA, cutB, 'DIFFERENCE')
boolean(halfB, cutA, 'DIFFERENCE')

# ---- 螺耳（跨缝，各半只加自己那侧）----
TAB_U = (19.0, 25.0)   # 径向范围
TAB_Z = [(2.0, 4.6), (7.0, 9.6)]
SCREW_U = (TAB_U[0] + TAB_U[1]) / 2
for half, sign in ((halfA, +1), (halfB, -1)):
    for i, (za, zb) in enumerate(TAB_Z):
        tab = add_box(f"tab_{half.name}_{i}", (TAB_U[0] + TAB_U[1]) / 2, sign * 1.25, (za + zb) / 2,
                      TAB_U[1] - TAB_U[0], 2.5, zb - za)
        boolean(half, tab, 'UNION')
    for i, (za, zb) in enumerate(TAB_Z):
        r_hole = 1.1 if sign > 0 else 0.75   # A: Ø2.2 过孔；B: Ø1.5 自攻底孔
        hole = add_cyl(f"hole_{half.name}_{i}", SCREW_U, 0, (za + zb) / 2, r_hole, 16)
        boolean(half, hole, 'DIFFERENCE')

# ---- 自检 + 导出 ----
def report(o):
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    print(f"{o.name}: verts={len(bm.verts)} faces={len(bm.faces)} nonmanifold_edges={nonman} vol={vol:.1f}")
    bm.free()
    return nonman, vol

for o in (halfA, halfB):
    report(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    path = os.path.join(OUT, o.name + ".stl")
    try:
        bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)
    except Exception:
        bpy.ops.export_mesh.stl(filepath=path, use_selection=True)
    print("exported", path, os.path.getsize(path), "bytes")

print("SEAM_ANGLE_DEG=", phi)
print("DONE")
