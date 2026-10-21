# 探针2b：用 evaluated 网格手动建 BVH（世界坐标，mm），判定 P03 内孔形式与轴外轮廓。
import bpy, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
BLEND = ROOT + r"\EffMeet2_NOMI_布局A_v6_紧凑候选.blend"
OUT = ROOT + r"\tools\order_probe2_rays.json"
N = 36

bpy.ops.wm.open_mainfile(filepath=BLEND)
dg = bpy.context.evaluated_depsgraph_get()

_cache = {}
def bvh_world(name):
    if name in _cache:
        return _cache[name]
    o = bpy.data.objects[name]
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [(mw @ v.co) * 1000.0 for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    n_orig = len(o.data.vertices) if o.data else -1
    ev.to_mesh_clear()
    b = BVHTree.FromPolygons(verts, polys, all_triangles=False)
    _cache[name] = (b, n_orig, len(verts))
    return _cache[name]

def first_hit(b, origin, direction):
    hit = b.ray_cast(Vector(origin), Vector(direction).normalized())
    if hit[0] is not None:
        p = hit[0]
        return math.hypot(p.x, p.y)
    return None

def bore(name, z, n=N):
    b = bvh_world(name)[0]
    return [first_hit(b, (0, 0, z), (math.cos(2*math.pi*k/n), math.sin(2*math.pi*k/n), 0)) for k in range(n)]

def outer(name, z, r0=40.0, n=N):
    b = bvh_world(name)[0]
    out = []
    for k in range(n):
        a = 2*math.pi*k/n
        d = first_hit(b, (r0*math.cos(a), r0*math.sin(a), z), (-math.cos(a), -math.sin(a), 0))
        out.append(d)
    return out

res = {"_meta": {}}
for name in ("N6_HOLLOW_LOAD_SHAFT", "N6_DRIVEN_64T", "N6_YAW_STOP_ARM", "N6_DRIVER_32T"):
    b, n_orig, n_eval = bvh_world(name)
    res["_meta"][name] = {"orig_verts": n_orig, "eval_verts": n_eval}

for z in (30, 44, 46, 49, 55, 63, 66, 80):
    res[f"shaft_outer_z{z}"] = outer("N6_HOLLOW_LOAD_SHAFT", z)
for z in (43, 46, 50):
    res[f"p03_bore_z{z}"] = bore("N6_DRIVEN_64T", z)
for z in (62.0, 62.7, 63.3):
    res[f"p13_bore_z{z}"] = bore("N6_YAW_STOP_ARM", z)
res["p04_bore_z46"] = bore("N6_DRIVER_32T", 46)

with open(OUT, "w", encoding="utf8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("PROBE2B_DONE ->", OUT)
for k, v in res.items():
    if k == "_meta":
        print("meta", json.dumps(v)); continue
    vals = [x for x in v if x is not None]
    if not vals:
        print(k, "NO_HIT"); continue
    print("%-18s min=%.2f max=%.2f n_none=%d" % (k, min(vals), max(vals), v.count(None)))
    if max(vals) - min(vals) > 0.15:
        print("   per-angle:", [None if x is None else round(x, 2) for x in v])
