# -*- coding: utf-8 -*-
"""
EffMeet2 v6 - 合并同类项打印盘生成器
把"数据齐 + 颜色一样 + 打印条件一样"的件合并到同一盘，输出可直接拖进 Bambu Studio 的 3MF。

源盘: print-split-v6/plates/*.3mf (几何起点排布, 256x256, margin8, gap10)
输出: outputs/print-ready/TMP-*.3mf + PRINT-PLAN.md

临时盘划分(依据 v6 MEASUREMENTS.csv / 购物车表 / PLATE-RUNBOOK):
  TMP-G3'  灰 0.16  A1/学校   P02                      (1件)
  TMP-B1'  黑 0.16  A1        P14,P27,P28              (3件)
  TMP-B23' 黑 0.20  A1        P05-P13,P15,P16,P17,P26,P29,P30,P31 (16件)
仍阻塞(不输出): P01,P03,P04,P18,P19,P20,P21,P22,P23,P24,P25
"""
import zipfile, re, os, json, csv, shutil
from xml.sax.saxutils import escape

SRC = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
OUT = r"C:\Users\94823\.qwenworkcn\workspace\mv8u5q649860hdr0\outputs\print-ready"
os.makedirs(OUT, exist_ok=True)

BED = 256.0
MARGIN = 8.0
GAP = 10.0
USABLE = BED - 2 * MARGIN  # 240

# ---------- 1. 读取源 3MF, 建立 part_id -> (object_xml, name) ----------
def load_plate(fname):
    """返回 {objectid: (name, object_xml_block)} 和 build items"""
    path = os.path.join(SRC, "plates", fname)
    z = zipfile.ZipFile(path)
    data = z.read("3D/3D.model").decode("utf-8")
    # 抓每个 <object ...>...</object>
    objs = {}
    for m in re.finditer(r'<object\s+id="(\d+)"[^>]*name="([^"]+)"[^>]*>.*?</object>', data, re.DOTALL):
        oid, name = m.group(1), m.group(2)
        objs[oid] = (name, m.group(0))
    return objs, data

# 源盘 -> 该盘所有 object
SRC_PLATES = {
    "G3": "plate_G3_v6.3mf",
    "B1": "plate_B1_v6.3mf",
    "B2": "plate_B2_v6.3mf",
    "B3": "plate_B3_v6.3mf",
}
plate_objs = {}
for pk, fn in SRC_PLATES.items():
    plate_objs[pk], _ = load_plate(fn)

# 建立 part_id(Pxx) -> (源盘key, object_xml, object_name)
# object name 形如 P05_N6_BEARING_TOWER_LOWER_SEAT
part_to_obj = {}
for pk, objs in plate_objs.items():
    for oid, (name, xml) in objs.items():
        pid = name.split("_")[0]  # P05
        part_to_obj[pid] = (pk, oid, name, xml)

# ---------- 2. 读取尺寸(footprint) ----------
with open(os.path.join(SRC, "plates", "plates.json"), "r", encoding="utf-8") as f:
    pj = json.load(f)
part_size = {}   # pid -> (w, d)  footprint on bed (stl_size_mm)
part_z = {}      # pid -> height
for pk, pdata in pj["plates"].items():
    for p in pdata["parts"]:
        pid = p["id"]
        sz = p.get("stl_size_mm")
        if sz:
            part_size[pid] = (float(sz[0]), float(sz[1]))
# 高度从 PARTS.csv size_mm 第三维
with open(os.path.join(SRC, "PARTS.csv"), "r", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        pid = row["id"]
        try:
            dims = [float(x) for x in re.split(r"[×x]", row["size_mm"])]
            if len(dims) == 3:
                part_z[pid] = dims[2]
        except Exception:
            pass

# ---------- 3. 定义临时盘 ----------
TMP_PLATES = [
    {
        "key": "TMP-G3p",
        "file": "TMP-G3p_GREY_016.3mf",
        "title": "EffMeet2 v6 TMP-G3p (grey 0.16)",
        "color": "灰",
        "layer": "0.16",
        "machine": "学校 · 灰料卷1",
        "brim": "5mm（防翘）",
        "support": "树状",
        "parts": ["P02"],
        "note": "底座上盖＋限位块；接缝圈朝下＝装配面，中心颈孔悬空需树支撑",
    },
    {
        "key": "TMP-B1p",
        "file": "TMP-B1p_BLACK_016.3mf",
        "title": "EffMeet2 v6 TMP-B1p (black 0.16)",
        "color": "黑",
        "layer": "0.16",
        "machine": "学校 · 黑料卷（唯一必须黑的盘）",
        "brim": "P27/P28 小件加",
        "support": "树状",
        "parts": ["P14", "P27", "P28"],
        "note": "外露件必须黑：短颈(P14)+隐私滑盖导轨(P27)+隐私滑片(P28)；P27/P28 不得融合，盯首层",
    },
    {
        "key": "TMP-B23p",
        "file": "TMP-B23p_GREY_020.3mf",
        "title": "EffMeet2 v6 TMP-B23p (grey 0.20) mechanism+brackets",
        "color": "灰",
        "layer": "0.20",
        "machine": "学校 · 灰料卷2",
        "brim": "一般不用",
        "support": "按需树状",
        "parts": ["P05","P06","P07","P08","P09","P10","P11","P12","P13","P15",
                  "P16","P17","P26","P29","P30","P31"],
        "note": "机构10件+支架6件合并改灰料(壳内不可见,RUNBOOK可灰)；空心轴P11竖直打(层向抗扭)；P05/P06/P11/P12轴承配合件等S1样片过",
    },
]

# ---------- 4. shelf packing ----------
def shelf_pack(parts):
    """parts: list of pid; 返回 {pid: (tx, ty)} 左下角坐标(含margin)"""
    # 按 footprint 高度(stl_size第二维=bed深度)降序，再按宽度降序
    items = []
    for pid in parts:
        w, d = part_size.get(pid, (20, 20))
        items.append((pid, w, d))
    items.sort(key=lambda x: (-x[2], -x[1]))  # 先按深度(行高)降序
    pos = {}
    x = MARGIN
    y = MARGIN
    row_h = 0.0
    for pid, w, d in items:
        if x + w > BED - MARGIN + 1e-6:
            # 换行
            x = MARGIN
            y += row_h + GAP
            row_h = 0.0
        pos[pid] = (round(x, 4), round(y, 4))
        x += w + GAP
        row_h = max(row_h, d)
    return pos

# ---------- 5. 生成 3MF ----------
CONTENT_TYPES = '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'
RELS = '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3D.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'

def build_3mf(plate_def):
    parts = plate_def["parts"]
    pos = shelf_pack(parts)
    resources = []
    build_items = []
    new_oid = 1
    layout_rows = []
    for pid in parts:
        if pid not in part_to_obj:
            print(f"  !! {pid} 不在源盘中, 跳过")
            continue
        src_pk, src_oid, name, obj_xml = part_to_obj[pid]
        # 重写 object id
        new_obj_xml = re.sub(r'<object\s+id="\d+"', f'<object id="{new_oid}"', obj_xml, count=1)
        resources.append(new_obj_xml)
        tx, ty = pos[pid]
        build_items.append(f'<item objectid="{new_oid}" transform="1 0 0 0 1 0 0 0 1 {tx:.4f} {ty:.4f} 0"/>')
        w, d = part_size.get(pid, (0, 0))
        layout_rows.append((pid, name, tx, ty, w, d, part_z.get(pid, 0)))
        new_oid += 1
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="zh-CN" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{escape(plate_def["title"])}</metadata>'
        f'<metadata name="Description">{escape(plate_def["note"])} | merged print-ready plate; slice in Bambu Studio per PLATE-RUNBOOK; CANDIDATE_NOT_RELEASED</metadata>'
        '<resources>' + "".join(resources) + '</resources>'
        '<build>' + "".join(build_items) + '</build>'
        '</model>'
    )
    outpath = os.path.join(OUT, plate_def["file"])
    with zipfile.ZipFile(outpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3D.model", model)
    return outpath, layout_rows

print("=== 生成临时打印盘 ===")
results = []
for pd in TMP_PLATES:
    print(f"\n[{pd['key']}] {pd['color']} {pd['layer']} {pd['machine']} -> {pd['file']}")
    outpath, layout = build_3mf(pd)
    sz = os.path.getsize(outpath)
    print(f"  写出 {outpath} ({sz/1024:.1f} KB), {len(layout)} 件")
    # 检查是否超出床面
    max_x = max((t[2] + t[4] for t in layout), default=0)
    max_y = max((t[3] + t[5] for t in layout), default=0)
    print(f"  占用: X {max_x:.1f} / Y {max_y:.1f} (床 256x256, 可用 {USABLE})")
    if max_x > BED - MARGIN + 1e-6 or max_y > BED - MARGIN + 1e-6:
        print(f"  ⚠️ 超出床面! 需缩减或分盘")
    results.append((pd, outpath, layout, max_x, max_y))

# ---------- 6. 保存布局 json 供核对 ----------
layout_dump = {}
for pd, outpath, layout, mx, my in results:
    layout_dump[pd["key"]] = {
        "file": pd["file"],
        "color": pd["color"],
        "layer": pd["layer"],
        "machine": pd["machine"],
        "occupied_x": round(mx, 2),
        "occupied_y": round(my, 2),
        "parts": [
            {"id": r[0], "name": r[1], "tx": r[2], "ty": r[3], "w": r[4], "d": r[5], "h": r[6]}
            for r in layout
        ],
    }
with open(os.path.join(OUT, "tmp-plates-layout.json"), "w", encoding="utf-8") as f:
    json.dump(layout_dump, f, ensure_ascii=False, indent=2)
print(f"\n布局 json: {os.path.join(OUT,'tmp-plates-layout.json')}")
print("完成")
