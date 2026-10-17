"""逐层薄壁可打印性审计 —— 模拟切片器周长生成，量出每圈墙的真实材料带宽。

为什么需要它（2026-10-16 P20 排查）
----------------------------------
既有检查有盲区，都只查"网格是否闭合/体积是否为正/该层面积是否为 0"：
  - production/delivery-validation.json 只查 "closed, positive volume"
  - production/export-byte-audit.json   只查 watertight / 零面积面 / 正体积
  - PRINT-LESSONS 教训22 的截面审计   只查 "该层面积是否为 0"
没有任何一关检查"这个特征切片器到底做不做得出来"。

本工具是为补这个盲区而写。**它对 P20 的结论是「几何无罪」**：
P20 轻触托座（Ø7 柱－Ø2.6 孔，环壁 2.20mm）逐层扫描 = 0 空层、k_max=3、
墙心残隙 0.098mm、thin_frac 未超标 —— 3 圈墙 + 0.098mm 残隙接近理想，
两对面墙珠子搭接即可填满，**不足以让 Ø2.6 孔消失**。
全 31 件扫描同样 0 空层、无任何 k_max≤1 的层。

所以 P20"圆孔打不出来"的原因不在模型，也不在墙层数（实测：墙层数设得比 k_max
大只是不生成多余圈，不会丢层）。排查方向应转向切片设置（支撑是否长进孔/口袋，
见 RUNBOOK:85 已诊断过的同类病根）与实际切片工程是否与仓库盘一致。

诚实边界：本工具**不是切片器**。它量的是几何可打印性，不能证明某次打印为何失败。

原理
----
两个互相独立的度量，缺一不可：

(A) 墙圈数探测 —— Bambu/Prusa **classic** 墙生成器从所有边界（外轮廓向内、孔向外）
    逐圈 inward offset，第 k 圈墙的中心线到边界距离：
        d_1 = 0.5 * E_outer                 （第一圈＝外墙，用外墙线宽）
        d_k = E_outer + (k-1.5) * E_inner   （k>=2，后续圈＝内墙，用内墙线宽）
    第 k 圈存在 ⟺ offset(-d_k) 非空。k_max 即几何能容纳的圈数。
    墙心残隙带宽用薄片等周关系估计：band ≈ 2A / P。
    **必须区分外/内墙线宽**：EffMeet2-v6 预设实测 outer=0.42、inner=0.45
    （读自 %APPDATA%/BambuStudio/user/<id>/process/EffMeet2-v6*.json）。
    早先用单一 E=0.42 会把 2.20mm 环壁算成 k_max=3／残隙 0.098mm（看似 4.3× 过挤），
    用真实双宽实为 k_max=2 有效＋第 3 圈只剩 0.005mm 退化脊线（会被丢弃），
    余 0.46mm 由 gap fill 接管 —— **完全可打印，不存在过挤**。
    **实测结论：把「墙层数」设得比 k_max 大不会丢层**，生成器只是不生成多余圈。
    → 所以 band 只作提醒（WARN），不作 FAIL。

(B) 薄材料占比（形态学开运算）—— opening(E/2)=offset(-E/2).offset(+E/2) 会抹掉
    所有厚度 < E 的材料；thin_frac = 1 - area(opening)/area(original)。
    **这才是「特征消失」的真机制**：薄于一道挤出的薄鳍，在「检查薄壁」关闭时
    被切片器整片丢弃（RUNBOOK:90 记录的 P07–P10/P16 现象）。
    度量 (A) 看不见它：薄鳍长在厚体上时，厚体让 offset 一直非空、k_max 很大，
    薄鳍被完全掩盖。→ thin_frac ≥ 2% 判 FAIL_THIN。

判级
  FAIL_THIN   thin_frac ≥ 2%          有特征薄于一道挤出，会被丢弃 → 勾检查薄壁/改 Arachne/加厚
  WARN_SLIVER 0.05mm < band < 0.20*E_inner  墙心残隙极窄（通常由 gap fill 接管，无害）
  WARN_TIGHT  0.20 ≤ band/E_inner < 0.60    墙心一道被压窄的填缝线（通常无害）
  OK          band ≥ 0.60*E_inner 或 band≈0（整数圈恰好填满，理想态）

k 圈墙恰好填满的壁厚（E_outer=0.42, E_inner=0.45）：W = 2*(E_outer+(k-1)*E_inner)
  k=1 → 0.84    k=2 → 1.74    k=3 → 2.64    k=4 → 3.54    k=5 → 4.44
介于两档之间的壁厚由 gap fill/稀疏填充补，属正常，不是缺陷。

用法
  python tools/thinwall_audit.py stl <file.stl> [<file2.stl> ...]
  python tools/thinwall_audit.py 3mf <plate.3mf>          # 审计盘内每个物件
  选项: --eouter 0.42  --einner 0.45  --lh 0.2  --step 1  --probe 8  --json <out.json>
退出码: 0=无 FAIL_THIN, 2=有 FAIL_THIN, 1=运行错误

依赖: numpy + manifold3d（路径同 finalize_exports.py，默认 local-only/mesh-tools，
可用 EFFMEET_MESH_TOOLS 覆盖）。manifold3d 不入库，故本工具属本机离线核对。
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOCAL_TOOLS = Path(os.environ.get("EFFMEET_MESH_TOOLS", str(ROOT / "local-only" / "mesh-tools")))
sys.path.insert(0, str(LOCAL_TOOLS))
try:
    import manifold3d as md
except ImportError as exc:  # pragma: no cover
    sys.exit(f"需要 manifold3d（预期在 {LOCAL_TOOLS}）：{exc}")

# ---- 判级阈值 ----
# band = k_max 圈墙生成后、壁厚中心剩下的残隙宽度。
#   ≈0        两对面墙恰好相遇，最理想（整数圈填满）
#   ~E        正好塞一道填充线，也理想
#   0<b<0.20E 退化薄片：塞不进又填不满 → 过挤 E/b 倍或留微孔（判 FAIL）
#   0.20~0.60E 被压窄的一道线（WARN，通常无害）
#   ≥0.60E    填充正常接管（CLEAN）
SOLID_EPS_MM = 0.05
SLIVER_RATIO = 0.20
TIGHT_RATIO = 0.60
# 截面积中「薄于一道挤出」的占比超过此值 → 有特征会被切片器丢弃（检查薄壁关闭时）
THIN_FRAC_WARN = 0.02

SEVERITY = {"EXACTLY_SOLID": 0, "CLEAN": 1, "TIGHT": 2, "SLIVER": 3}


def classify(band: float, E: float) -> str:
    if band <= SOLID_EPS_MM:
        return "EXACTLY_SOLID"
    r = band / E
    if r < SLIVER_RATIO:
        return "SLIVER"
    if r < TIGHT_RATIO:
        return "TIGHT"
    return "CLEAN"


# ---------------- 几何读入 ----------------
def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:4096]:
        raise ValueError(f"{path.name}: 本工具只读二进制 STL")
    n = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50 * n:
        raise ValueError(f"{path.name}: STL 长度不符（期望 {84+50*n}，实得 {len(data)}）")
    rec = struct.Struct("<12fH")
    tris = np.zeros((n, 3, 3), dtype=np.float64)
    for i in range(n):
        tris[i] = np.array(rec.unpack_from(data, 84 + i * rec.size)[3:12]).reshape(3, 3)
    return tris


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def extract_3mf(path: Path, outdir: Path) -> list[tuple[str, Path]]:
    """把 3MF 盘里每个 object 写成独立二进制 STL（盘内件常无仓内 STL 源）。"""
    with zipfile.ZipFile(path) as z:
        entry = next((n for n in z.namelist() if n.lower().endswith(".model")), None)
        if entry is None:
            raise ValueError(f"{path.name}: 盘内无 *.model，几何未内嵌")
        root = ET.fromstring(z.read(entry))
    out: list[tuple[str, Path]] = []
    for ob in (c for c in root.iter() if _strip_ns(c.tag) == "object"):
        name = ob.get("name") or f"obj{ob.get('id')}"
        verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z")))
                 for v in (c for c in ob.iter() if _strip_ns(c.tag) == "vertex")]
        tris = [(int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
                for t in (c for c in ob.iter() if _strip_ns(c.tag) == "triangle")]
        if not verts or not tris:
            continue
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in name)
        dst = outdir / f"{safe}.stl"
        with dst.open("wb") as fh:
            fh.write(b"EFFMEET2 THINWALL AUDIT EXTRACT".ljust(80, b" "))
            fh.write(struct.pack("<I", len(tris)))
            for a, b, c in tris:
                p1, p2, p3 = np.array(verts[a]), np.array(verts[b]), np.array(verts[c])
                nrm = np.cross(p2 - p1, p3 - p1)
                ln = np.linalg.norm(nrm)
                nrm = nrm / ln if ln else np.zeros(3)
                fh.write(struct.pack("<12fH", *nrm, *p1, *p2, *p3, 0))
        out.append((name, dst))
    return out


def to_manifold(tris: np.ndarray) -> "md.Manifold":
    verts, faces, index = [], [], {}
    for t in tris:
        ids = []
        for v in t:
            key = (round(float(v[0]), 6), round(float(v[1]), 6), round(float(v[2]), 6))
            if key not in index:
                index[key] = len(verts)
                verts.append(key)
            ids.append(index[key])
        faces.append(ids)
    mesh = md.Mesh64(np.array(verts, dtype=np.float64),
                     np.array(faces, dtype=np.uint64), tolerance=0.0001)
    m = md.Manifold(mesh)
    if m.status() != md.Error.NoError:
        mesh.merge()
        m = md.Manifold(mesh)
    return m


# ---------------- 截面量测 ----------------
def _poly_area(p) -> float:
    a, n = 0.0, len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2.0


def _poly_perim(p) -> float:
    s, n = 0.0, len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        s += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return s


def section_metrics(cs) -> tuple[float, float]:
    """返回 (净面积, 总周长)。净面积按外轮廓正、孔负累加。"""
    if cs.is_empty():
        return 0.0, 0.0
    area = perim = 0.0
    for p in cs.to_polygons():
        if len(p) < 3:
            continue
        area += _poly_area(p)          # 带符号：外正内负
        perim += abs(_poly_perim(p))
    return area, perim


def thin_fraction(cs, E: float) -> float:
    """形态学开运算：量出「薄于一道挤出」的材料占比。

    opening(E/2) = offset(-E/2).offset(+E/2) 会抹掉所有厚度 < E 的材料。
    1 - area(opening)/area(original) 就是薄材料占比。

    为什么必须有这一项（本工具的盲区修正）
    --------------------------------------
    下面的 k_max 探测量的是**整个截面**能否容纳 k 圈墙。若一片 W<E 的薄鳍
    长在厚体上，厚体会让 offset 一直非空、k_max 很大，薄鳍被完全掩盖 ——
    而 RUNBOOK:90 记录的"薄于喷嘴的薄鳍被切片丢弃"正是这种形态。
    只有开运算能把它单独量出来。
    """
    a0, _ = section_metrics(cs)
    if a0 <= 1e-9:
        return 0.0
    try:
        opened = cs.offset(-E / 2.0).offset(E / 2.0)
    except Exception:
        return float("nan")
    a1, _ = section_metrics(opened)
    return max(0.0, 1.0 - a1 / a0)


def audit_part(stl: Path, label: str, e_outer: float, e_inner: float, lh: float,
               step: int, probe: int, verbose: bool) -> dict:
    tris = read_stl(stl)
    man = to_manifold(tris)
    bb = man.bounding_box()
    lo, hi = np.array(bb[:3], dtype=float), np.array(bb[3:], dtype=float)
    z0, z1 = float(lo[2]), float(hi[2])
    height = z1 - z0
    n_layers = max(1, int(round(height / lh)))

    res = {
        "label": label, "stl": str(stl), "tris": int(len(tris)),
        "genus": int(man.genus()), "volume_mm3": round(float(man.volume()), 3),
        "size_mm": [round(float(hi[i] - lo[i]), 3) for i in range(3)],
        "height_mm": round(height, 3), "layers": n_layers,
        "manifold_status": str(man.status()),
        "e_outer": e_outer, "e_inner": e_inner, "lh": lh,
        "empty_layers": [], "rows": [],
    }

    worst = None
    kmax_hist: dict[int, int] = {}
    thin_max, thin_layer = 0.0, None
    for i in range(0, n_layers, step):
        z = z0 + (i + 0.5) * lh
        if z >= z1:
            break
        cs = man.slice(float(z))
        a0, p0 = section_metrics(cs)
        if a0 <= 1e-9:
            res["empty_layers"].append([i, round(z, 3)])
            continue
        # 逐圈探测：第 k 圈墙中心线到边界的距离 d_k（Bambu/Prusa classic 生成器）
        #   d_1 = 0.5*E_outer                （第一圈是外墙，用外墙线宽）
        #   d_k = E_outer + (k-1.5)*E_inner  （k>=2，后续圈用内墙线宽）
        # 第 k 圈存在 ⟺ offset(-d_k) 非空。
        # ⚠️ 必须区分外/内墙线宽：实测 EffMeet2-v6 预设 outer=0.42、inner=0.45。
        #    早先用单一 E=0.42 会把 k_max 多算一圈、并把残隙算小（2.20mm 环壁
        #    单宽算出 k_max=3/残隙0.098，双宽实为 k_max=2 有效 + 第3圈仅 0.005mm
        #    退化脊线会被丢弃）。见 PRINT-LESSONS 教训30 更正。
        areas, perims = [], []
        for k in range(1, probe + 1):
            d = 0.5 * e_outer if k == 1 else e_outer + (k - 1.5) * e_inner
            try:
                a, p = section_metrics(cs.offset(-d))
            except Exception:
                a, p = 0.0, 0.0
            areas.append(a)
            perims.append(p)
        # 退化脊线过滤：残隙小于内墙线宽的 5% 时，切片器会丢弃该圈
        MIN_SLIVER = 0.05 * e_inner
        kmax = 0
        for k in range(1, probe + 1):
            if areas[k - 1] > 1e-9:
                band_k = (2.0 * areas[k - 1] / perims[k - 1]
                          if perims[k - 1] > 1e-9 else 0.0)
                if band_k > MIN_SLIVER:
                    kmax = k
        if kmax == 0:
            band, cls = 0.0, "SLIVER"
        else:
            band = 2.0 * areas[kmax - 1] / perims[kmax - 1] if perims[kmax - 1] > 1e-9 else 0.0
            cls = classify(band, e_inner)
        kmax_hist[kmax] = kmax_hist.get(kmax, 0) + 1
        tf = thin_fraction(cs, e_outer)
        row = {"layer": i, "z": round(z, 3), "a_net": round(a0, 4),
               "k_max": kmax, "band_mm": round(band, 4),
               "over_extrude": round(e_inner / band, 2) if band > 1e-6 else None,
               "thin_frac": round(tf, 5),
               "class": cls}
        res["rows"].append(row)
        if tf == tf and tf > thin_max:      # tf==tf 排除 nan
            thin_max, thin_layer = tf, i
        # 最坏 = 严重度最高；同级取带宽最小（EXACTLY_SOLID 除外，它带宽 0 是好事）
        if worst is None:
            worst = row
        else:
            sev_new, sev_old = SEVERITY[cls], SEVERITY[worst["class"]]
            if sev_new > sev_old or (sev_new == sev_old and sev_new > 0
                                      and band < worst["band_mm"]):
                worst = row

    res["k_max_hist"] = {str(k): v for k, v in sorted(kmax_hist.items())}
    res["worst"] = worst
    res["thin_frac_max"] = round(thin_max, 5)
    res["thin_frac_layer"] = thin_layer
    if worst:
        res["required_wall_loops"] = worst["k_max"]

    # 判定优先级：真正会「特征消失」的是 thin_frac（材料薄于一道挤出，
    # 检查薄壁关闭时被切片器整片丢弃）。band 只是墙心残隙，两对面墙的
    # 珠子会互相搭接填满，band<E 时并不产生空洞，故只作提醒不作 FAIL。
    if worst is None:
        res["verdict"] = "NO_SECTION"
    elif thin_max >= THIN_FRAC_WARN:
        res["verdict"] = "FAIL_THIN"
    elif worst["class"] == "SLIVER":
        res["verdict"] = "WARN_SLIVER"
    elif worst["class"] == "TIGHT":
        res["verdict"] = "WARN_TIGHT"
    else:
        res["verdict"] = "OK"

    if verbose:
        print("=" * 86)
        print(f"PART: {label}")
        print("=" * 86)
        print(f"  tris={res['tris']}  genus={res['genus']}  volume={res['volume_mm3']} mm^3"
              f"  status={res['manifold_status']}")
        print(f"  size={res['size_mm'][0]} x {res['size_mm'][1]} x {res['size_mm'][2]} mm"
              f"  -> {n_layers} layers @ {lh}")
        print(f"  EMPTY layers: {len(res['empty_layers'])} {res['empty_layers'][:8]}")
        print(f"  k_max histogram: {res['k_max_hist']}")
        if worst:
            print(f"  WORST band layer {worst['layer']} (z={worst['z']}): k_max={worst['k_max']} "
                  f"band={worst['band_mm']}mm -> {worst['class']}"
                  + (f"  过挤 {worst['over_extrude']}x" if worst["over_extrude"] else ""))
        print(f"  THIN material (<1 extrusion wide): max {thin_max*100:.2f}% of section"
              f" at layer {thin_layer}")
        print(f"  VERDICT: {res['verdict']}")
        if res["verdict"] == "FAIL_THIN":
            print(f"  FIX: 勾**检查薄壁**（Detect thin wall）让薄鳍以单道薄壁挤出，"
                  f"或墙生成器改 **Arachne**（变宽墙）；"
                  f"若该薄鳍是功能特征，治本＝把它加厚到 ≥{e_outer:.2f}mm")
        elif res["verdict"] in ("WARN_SLIVER", "WARN_TIGHT") and worst:
            print(f"  NOTE: 墙心残隙 {worst['band_mm']}mm（{worst['over_extrude']}× 线宽）。"
                  f"两对面墙珠子会搭接填满，通常无害；仅当该处出现缺料/透光才需处理")
        print()
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["stl", "3mf"])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--eouter", type=float, default=0.42,
                    help="外墙线宽 outer_wall_line_width（EffMeet2-v6 预设实测 0.42）")
    ap.add_argument("--einner", type=float, default=0.45,
                    help="内墙线宽 inner_wall_line_width（EffMeet2-v6 预设实测 0.45）")
    ap.add_argument("--lh", type=float, default=0.2, help="层高")
    ap.add_argument("--step", type=int, default=1, help="每 N 层抽一层（大件提速）")
    ap.add_argument("--probe", type=int, default=8, help="最多探测几圈墙")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    ap.add_argument("--json", help="把完整结果写到此 JSON")
    args = ap.parse_args()

    results: list[dict] = []
    tmp = tempfile.TemporaryDirectory(prefix="thinwall-3mf-")
    try:
        for raw in args.paths:
            p = Path(raw)
            if not p.exists():
                print(f"!! 跳过不存在的文件: {p}", file=sys.stderr)
                continue
            if args.kind == "stl":
                results.append(audit_part(p, p.stem, args.eouter, args.einner,
                                          args.lh, args.step,
                                          args.probe, not args.quiet))
            else:
                for name, stl in extract_3mf(p, Path(tmp.name)):
                    results.append(audit_part(stl, name, args.eouter, args.einner,
                                              args.lh, args.step,
                                              args.probe, not args.quiet))
    finally:
        tmp.cleanup()

    if not results:
        print("没有可审计的几何", file=sys.stderr)
        return 1

    print("=" * 104)
    print(f"汇总  (外墙={args.eouter} 内墙={args.einner}  lh={args.lh}  step={args.step})")
    print("=" * 104)
    print(f"{'part':<34} {'h mm':>6} {'layers':>6} {'empty':>5} {'k_max':>5} "
          f"{'band':>7} {'thin%':>7} {'class':<14} verdict")
    print("-" * 104)
    fails = warns = 0
    for r in results:
        w = r["worst"] or {}
        print(f"{r['label'][:34]:<34} {r['height_mm']:>6.2f} {r['layers']:>6} "
              f"{len(r['empty_layers']):>5} {w.get('k_max','-'):>5} {w.get('band_mm',''):>7} "
              f"{r['thin_frac_max']*100:>7.2f} {w.get('class','-'):<14} {r['verdict']}")
        if r["verdict"] == "FAIL_THIN":
            fails += 1
        elif r["verdict"].startswith("WARN"):
            warns += 1
    print("-" * 104)
    print(f"共 {len(results)} 件：FAIL_THIN（有特征薄于一道挤出、会被丢弃）{fails} 件，"
          f"WARN {warns} 件，其余 OK")
    print(f"thin% = 截面积中厚度 < 外墙线宽({args.eouter}mm) 的占比（形态学开运算量得）；"
          f">= {THIN_FRAC_WARN*100:.0f}% 判 FAIL_THIN")
    print("k 圈墙恰好填满的壁厚 W=2*(外+(k-1)*内): " +
          "  ".join(f"k={k}->{2*(args.eouter+(k-1)*args.einner):.2f}"
                    for k in range(1, 6)))
    print("注1: band≈0 是「整数圈恰好填满」的理想态，不是缺陷。")
    print("注2: band 在 (0,内墙线宽) 时由 gap fill/填充接管，不产生空洞 —— 故 band 只作提醒。")
    print("注3: 墙层数设得比 k_max 大**不会**丢层，生成器只是不生成多余圈（实测证实）。")
    print("注4: 第 k 圈中心线距边界 d_k = 0.5*外 (k=1) / 外+(k-1.5)*内 (k>=2)；"
          "残隙 < 5%内墙线宽 视为退化脊线，切片器会丢弃该圈。")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"e_outer": args.eouter, "e_inner": args.einner,
                        "lh": args.lh, "step": args.step,
                        "scope": "per-layer thin-wall printability; NOT a slicer run",
                        "parts": results}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"JSON: {args.json}")
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
