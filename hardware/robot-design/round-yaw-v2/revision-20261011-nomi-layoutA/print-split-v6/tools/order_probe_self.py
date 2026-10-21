# 10-20 装配顺序探针（自查版）：对 v6 场景 evaluated mesh 采样半径剖面，
# 判定 轴肩凸台方向 / P06-P05 轴承座唇结构 / P03 可装性 / P13 轴向定位 / 限位块归属。
# 只读 blend，结果写 order_probe_self.json。运行：
# "D:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python tools/order_probe_self.py
import bpy, json, math

ROOT = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
BLEND = ROOT + r"\EffMeet2_NOMI_布局A_v6_紧凑候选.blend"
OUT = ROOT + r"\tools\order_probe_self.json"

bpy.ops.wm.open_mainfile(filepath=BLEND)
dg = bpy.context.evaluated_depsgraph_get()

def verts(name):
    o = bpy.data.objects[name]
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [(mw @ v.co) * 1000.0 for v in me.vertices]  # 场景单位为米 → 毫米
    ev.to_mesh_clear()
    return pts

def profile(name, z0, z1, step=0.5):
    bands = {}
    for p in verts(name):
        if z0 - 1e-6 <= p.z <= z1 + 1e-6:
            i = int((p.z - z0) // step)
            r = math.hypot(p.x, p.y)
            b = bands.setdefault(i, [1e9, 0.0, 0])
            b[0] = min(b[0], r); b[1] = max(b[1], r); b[2] += 1
    return [
        {"z": round(z0 + i * step, 2), "rmin": round(b[0], 2), "rmax": round(b[1], 2), "n": b[2]}
        for i, b in sorted(bands.items())
    ]

res = {}
res["shaft_profile_z26_88"] = profile("N6_HOLLOW_LOAD_SHAFT", 26, 88, 0.5)
res["p06_profile_z50_63"] = profile("N6_UPPER_BEARING_SEAT", 50, 63, 0.5)
res["p05_profile_z4_43"] = profile("N6_BEARING_TOWER_LOWER_SEAT", 4, 43, 0.5)
res["p03_profile_z39_54"] = profile("N6_DRIVEN_64T", 39, 54, 0.5)
res["p13_profile_z60_66"] = profile("N6_YAW_STOP_ARM", 60, 66, 0.4)

lid = verts("N6_BASE_LID")
def in_stop(p):
    return (9.0 <= p.x <= 21.0 and abs(p.y) >= 18.0 and 61.0 <= p.z <= 65.5)
res["lid_stop_blocks"] = {
    "n_plus_y": sum(1 for p in lid if in_stop(p) and p.y > 0),
    "n_minus_y": sum(1 for p in lid if in_stop(p) and p.y < 0),
    "lid_bbox_z": [round(min(p.z for p in lid), 1), round(max(p.z for p in lid), 1)],
}

# 轴承代理实际位置（世界坐标 bbox）供对照
for key, obj in [("bearing_upper", "N6_BEARING_UPPER"), ("bearing_lower", "N6_BEARING_LOWER")]:
    o = bpy.data.objects[obj]
    ev = o.evaluated_get(dg)
    mw = ev.matrix_world
    cs = [(mw @ v.co) * 1000.0 for v in ev.to_mesh().vertices]
    ev.to_mesh_clear()
    res[key + "_bbox"] = {
        "z": [round(min(c.z for c in cs), 2), round(max(c.z for c in cs), 2)],
        "rmax": round(max(math.hypot(c.x, c.y) for c in cs), 2),
    }

with open(OUT, "w", encoding="utf8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("PROBE_DONE ->", OUT)
for k in ("lid_stop_blocks", "bearing_upper_bbox", "bearing_lower_bbox"):
    print(k, json.dumps(res[k]))
# 轴剖面压缩打印：只出 rmax 变化点
prev = None
for row in res["shaft_profile_z26_88"]:
    if row["rmax"] != prev:
        print("SHAFT z=%.1f rmax=%.2f" % (row["z"], row["rmax"]))
        prev = row["rmax"]
for tag in ("p06_profile_z50_63", "p05_profile_z4_43"):
    print("--", tag)
    prev = None
    for row in res[tag]:
        if row["rmin"] != prev:
            print("  z=%.1f rmin=%.2f" % (row["z"], row["rmin"]))
            prev = row["rmin"]
