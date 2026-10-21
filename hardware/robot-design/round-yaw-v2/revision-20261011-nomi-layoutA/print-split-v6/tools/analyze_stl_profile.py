"""对打印 STL 做水平截面射线剖面 v2：自动找轴心（XY 包围盒中心），按 STL 本地 z 采样。
验证：P11 肩台/平带范围；P03 内孔平面。纯 python。
"""
import struct, math, json, os

CS = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6\candidate-stl"
OUT = os.path.join(CS, "..", "tools", "stl_profile_result.json")

def load_stl(path):
    with open(path, "rb") as f:
        head = f.read(84)
        n = struct.unpack("<I", head[80:84])[0]
        data = f.read(n * 50)
        tris = []
        for i in range(n):
            off = i * 50 + 12
            v = struct.unpack("<9f", data[off:off + 36])
            tris.append((v[0:3], v[3:6], v[6:9]))
        return tris

def bbox(tris):
    xs = [p[0] for t in tris for p in t]; ys = [p[1] for t in tris for p in t]; zs = [p[2] for t in tris for p in t]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))

def slice_segments(tris, z, cx, cy):
    segs = []
    for t in tris:
        zs = [p[2] for p in t]
        pts = []
        for i in range(3):
            a, b = t[i], t[(i + 1) % 3]
            if (a[2] - z) * (b[2] - z) < 0:
                f = (z - a[2]) / (b[2] - a[2])
                pts.append((a[0] + f * (b[0] - a[0]) - cx, a[1] + f * (b[1] - a[1]) - cy))
        if len(pts) == 2:
            (x1, y1), (x2, y2) = pts
            if abs(x1 - x2) > 1e-9 or abs(y1 - y2) > 1e-9:
                segs.append((x1, y1, x2, y2))
    return segs

def ray_first(segs, theta):
    dx, dy = math.cos(theta), math.sin(theta)
    best = None
    for (x1, y1, x2, y2) in segs:
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (x1 * ey - y1 * ex) / den
        if t <= 1e-9:
            continue
        if abs(ex) > 1e-9:
            u = (t * dx - x1) / ex
        else:
            u = (t * dy - y1) / ey
        if -1e-9 <= u <= 1 + 1e-9:
            if best is None or t < best:
                best = t
    return best

def profile(tris, z, cx, cy, n=36):
    segs = slice_segments(tris, z, cx, cy)
    if not segs:
        return None
    return [ray_first(segs, 2 * math.pi * k / n) for k in range(n)]

def show(vals):
    if vals is None:
        return "NO_SLICE"
    vv = [v for v in vals if v is not None]
    if not vv:
        return "NO_HIT"
    return "min=%.2f max=%.2f" % (min(vv), max(vv))

res = {}
p11 = load_stl(os.path.join(CS, "P11_HOLLOW_LOAD_SHAFT_UNVERIFIED.stl"))
p03 = load_stl(os.path.join(CS, "P03_DRIVEN_64T_UNVERIFIED.stl"))
b11, b03 = bbox(p11), bbox(p03)
c11 = ((b11[0] + b11[1]) / 2, (b11[2] + b11[3]) / 2)
c03 = ((b03[0] + b03[1]) / 2, (b03[2] + b03[3]) / 2)
res["_p11_bbox"] = [round(v, 2) for v in b11] + ["c", round(c11[0], 2), round(c11[1], 2)]
res["_p03_bbox"] = [round(v, 2) for v in b03] + ["c", round(c03[0], 2), round(c03[1], 2)]

# STL z = 场景 z − 26（P11 长 60）；场景：轴承带33-40/53-60、驱动平42.2-50.6、肩60-61.4、上D 61.8+
# → STL：轴承带 7-14 / 27-34、驱动平 16.2-24.6、肩 34-35.4、上D 35.8+
for z in (8, 14, 16.5, 18, 20, 22, 24.5, 26, 30, 33.5, 34.2, 34.8, 35.2, 35.6, 37, 45, 58):
    vals = profile(p11, z, c11[0], c11[1])
    res[f"P11_z{z}"] = show(vals)
    if vals and (lambda vv: vv and max(vv) - min(vv) > 0.15)([v for v in vals if v]):
        res[f"P11_z{z}_ang"] = [None if v is None else round(v, 2) for v in vals]

# P03：STL z0-10.6，中部 5.3
for z in (1.0, 5.3, 9.6):
    vals = profile(p03, z, c03[0], c03[1])
    res[f"P03_z{z}"] = show(vals)
    res[f"P03_z{z}_ang"] = None if vals is None else [None if v is None else round(v, 2) for v in vals]

with open(OUT, "w", encoding="utf8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("STL_PROFILE_V2 ->", OUT)
for k, v in res.items():
    print(k, v)
