"""打印盘登记与层数核对 —— 扫 plates-merged/*.3mf，量出盘内真实内容与隐含层数。

为什么需要（2026-10-16）
----------------------
两个真实缺陷：
1. **有盘在 RUNBOOK 里没有条目**（如 TMP-INTERN2-DEC / TMP-MICHOLDER / TMP-BVIS*），
   于是该盘的支撑/Brim/层高设置无处可查，件一换盘对症设置就丢（PRINT-LESSONS 教训31）。
2. **实际打印的工程与仓库盘对不上**：App 截图显示 128/128 层，但 INTERN2-DEC
   最高件 14.4mm、0.20 层高只有 72 层。层数是最容易核对的指纹 —— 对不上就说明
   Bambu 里的工程被改过（层高/朝向/内容），此时任何基于仓库盘的分析都不适用于实物。

本工具输出每盘：物件清单、三角面数、bbox、最高件、按文件名层高隐含的层数，
以及"该件是否在 candidate-stl/ 有源"（无源件见 PRINT-LESSONS 教训33）。

用法
  python tools/plate_registry.py                # 扫 plates-merged/，打印表 + 写 JSON
  python tools/plate_registry.py --match 128    # 反查：哪一盘在哪个层高下等于 128 层
  python tools/plate_registry.py --md           # 额外输出可贴进 RUNBOOK 的 markdown 表
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PLATES = ROOT / "plates-merged"
CSTL = ROOT / "candidate-stl"
PROD = ROOT / "production"

# 文件名里的层高标记 → mm
LH_TAGS = {"_008": 0.08, "_010": 0.10, "_012": 0.12, "_016": 0.16,
           "_020": 0.20, "_024": 0.24, "_028": 0.28, "_030": 0.30}
COMMON_LH = [0.08, 0.10, 0.12, 0.16, 0.20, 0.24, 0.28, 0.30]


def _strip(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def read_plate(path: Path) -> list[dict]:
    """从 3MF 读出每个 object 的名字/三角面数/bbox。"""
    with zipfile.ZipFile(path) as z:
        entry = next((n for n in z.namelist() if n.lower().endswith(".model")), None)
        if entry is None:
            return []
        root = ET.fromstring(z.read(entry))
    objs = []
    for ob in (c for c in root.iter() if _strip(c.tag) == "object"):
        name = ob.get("name") or f"obj{ob.get('id')}"
        xs, ys, zs = [], [], []
        for v in (c for c in ob.iter() if _strip(c.tag) == "vertex"):
            xs.append(float(v.get("x")))
            ys.append(float(v.get("y")))
            zs.append(float(v.get("z")))
        ntri = sum(1 for c in ob.iter() if _strip(c.tag) == "triangle")
        if not xs:
            continue
        objs.append({
            "name": name, "tris": ntri,
            "size_mm": [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3),
                        round(max(zs) - min(zs), 3)],
            "z_min": round(min(zs), 3), "z_max": round(max(zs), 3),
        })
    return objs


def stl_tris(path: Path) -> int | None:
    try:
        d = path.read_bytes()
        return struct.unpack_from("<I", d, 80)[0] if len(d) >= 84 else None
    except OSError:
        return None


def implied_layers(maxh: float, lh: float) -> int:
    """层数 = ceil(高度 / 层高)，但**先把高度圆整到微米**。

    不圆整会多算一层：STL 用 float32 存 8.6 实际是 8.60000228881836，
    8.60000228881836/0.2 = 43.000011 → ceil = **44**（真值 43）。
    本工具输出的层数被写进 PLATE-RUNBOOK §6 当作与 Bambu App 比对的**指纹**，
    差一层就会在核对时产生假警报（本次排查已因类似误判浪费过时间）。
    """
    return math.ceil(round(maxh, 3) / lh - 1e-9)


def part_id(name: str) -> str:
    # 必须带后缀字母：P18T（容差版）与 P18（原托架）是两个不同件，
    # 只取 P\d+ 会把 P18T 误判成 P18 从而误报"有源"
    m = re.match(r"(P\d+[A-Za-z]?)", name)
    return m.group(1) if m else "?"


def has_source(pid: str) -> bool:
    """该件在 candidate-stl/ 里有没有 STL 源（无源件＝教训33 的隐患）。"""
    if pid == "?":
        return False
    return any(p.name.startswith(pid + "_") for p in CSTL.glob("*.stl"))


def layer_height_of(name: str) -> float | None:
    for tag, lh in LH_TAGS.items():
        if tag in name:
            return lh
    return None


def scan(plates_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(plates_dir.glob("*.3mf")):
        objs = read_plate(p)
        lh = layer_height_of(p.name)
        maxh = max((o["z_max"] - o["z_min"] for o in objs), default=0.0)
        # 盘内物件是排布在床面上的，z_max 即高度；用最大 z_max 作为总高
        maxh = max((o["z_max"] for o in objs), default=0.0)
        rows.append({
            "file": p.name, "bytes": p.stat().st_size, "layer_height": lh,
            "objects": len(objs), "max_height_mm": round(maxh, 3),
            "layers_at_named_lh": implied_layers(maxh, lh) if lh else None,
            "parts": [{**o, "pid": part_id(o["name"]),
                       "has_stl_source": has_source(part_id(o["name"]))} for o in objs],
            "no_source_parts": sorted({part_id(o["name"]) for o in objs
                                       if not has_source(part_id(o["name"]))}),
        })
    return rows


def reverse_match(rows: list[dict], target: int) -> list[str]:
    """反查哪一盘在哪个层高下恰好等于 target 层。"""
    hits = []
    for r in rows:
        for lh in COMMON_LH:
            n = implied_layers(r["max_height_mm"], lh)
            if n == target:
                hits.append(f"{r['file']}  @ lh={lh}  maxH={r['max_height_mm']}mm  -> {n} 层")
    return hits


def main() -> int:
    # Windows 控制台默认 GBK，中文/符号会 UnicodeEncodeError；强制 UTF-8 输出
    if hasattr(sys.stdout, "buffer"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(PLATES))
    ap.add_argument("--match", type=int, help="反查等于此层数的盘×层高组合")
    ap.add_argument("--md", action="store_true", help="输出可贴进 RUNBOOK 的 markdown 表")
    ap.add_argument("--json", default=str(PROD / "plate-registry.json"))
    args = ap.parse_args()

    d = Path(args.dir)
    if not d.exists():
        print(f"目录不存在: {d}", file=sys.stderr)
        return 1
    rows = scan(d)

    if args.match:
        print(f"反查 {args.match} 层：")
        hits = reverse_match(rows, args.match)
        for h in hits or ["  （无任何盘×常用层高组合等于该层数）"]:
            print("  " + h)
        print()

    print(f"{'plate':<34}{'lh':>5}{'objs':>5}{'maxH':>8}{'layers':>7}  no-source")
    print("-" * 92)
    for r in rows:
        lh = f"{r['layer_height']:.2f}" if r["layer_height"] else "?"
        lay = r["layers_at_named_lh"] if r["layers_at_named_lh"] else "?"
        ns = ",".join(r["no_source_parts"]) or "-"
        print(f"{r['file'][:34]:<34}{lh:>5}{r['objects']:>5}"
              f"{r['max_height_mm']:>8.2f}{lay:>7}  {ns}")

    if args.md:
        print("\n\n<!-- 以下为 tools/plate_registry.py 自动生成，可贴进 PLATE-RUNBOOK -->")
        print("| 盘文件 | 层高 | 件数 | 最高件 | 隐含层数 | 盘内物件（三角面数） | 无仓内源 |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            objs = "<br>".join(f"`{o['name']}` {o['tris']}面 {o['size_mm'][0]:g}×"
                               f"{o['size_mm'][1]:g}×{o['size_mm'][2]:g}" for o in r["parts"])
            lh = f"{r['layer_height']:.2f}" if r["layer_height"] else "?"
            lay = r["layers_at_named_lh"] or "?"
            ns = ", ".join(r["no_source_parts"]) or "—"
            print(f"| `{r['file']}` | {lh} | {r['objects']} | {r['max_height_mm']:.2f}mm "
                  f"| {lay} | {objs} | {ns} |")

    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps({
        "scope": "plate content + implied layer count from 3MF geometry; NOT a slicer result",
        "note": "layers_at_named_lh 用文件名里的层高标记推算；Bambu 实际层数还受首层厚/支撑影响，"
                "仅用于与 App 显示层数做指纹比对",
        "plates": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nJSON: {args.json}")

    nosrc = {r["file"]: r["no_source_parts"] for r in rows if r["no_source_parts"]}
    if nosrc:
        print(f"\n⚠️ 含无仓内源物件的盘 {len(nosrc)} 个（PRINT-LESSONS 教训33）：")
        for f, ps in nosrc.items():
            print(f"    {f}: {', '.join(ps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
