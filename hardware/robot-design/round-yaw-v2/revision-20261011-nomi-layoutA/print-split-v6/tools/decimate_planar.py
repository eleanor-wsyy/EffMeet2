"""平面融解减面（DECIMATE/DISSOLVE）—— 带自校验，不再静默产出"没减面"的假结果。

2026-10-16 查出的真缺陷（旧版脚本）
----------------------------------
1. **"减面"对 STL 是 no-op —— 面数量纲搞错了（最重要）。**
   DECIMATE/DISSOLVE 把共面三角形合并成 **n-gon**：P04 在 5.0° 下
   `len(bm.faces)` 从 4896 降到 **1266**，但那是**多边形数**。STL 只能存三角形，
   n-gon 重新三角化后**仍是 4896**。实测导出核对：写入 4896、读回 4896。
   → HANDOFF 记的"P04 4896→1266（5°，vol 0.000%）"是**拿三角面数比多边形数**，
     量纲错误；P04 的减面从未真正生效，机房老师反映的"网格过密"对 P04 没解决。
   → P02 不同：18134→13614 是**真的**三角面减少（平面区有内部顶点可删）。
     但入仓的 13614 用本脚本任何角度都复现不出（1.5°→5231 三角面），来源不明。
   本版因此**同时记录 tris_* 与 polys_***，并以 tris_ 作为唯一判定依据。
2. **OUT 指向另一个会话的临时目录**（`workspace/mv8u5q649860hdr0/v6rebuild/new-stl`），
   仓库内无法复现；`plates-merged/decimated/P04_decimated.stl` 因此是 4896 面的
   未减面副本，而 `TMP-INTERN2-DEC_GREY_020.3mf` 盘内 `P04_DRIVER32T_dec` 也正是 4896 面。
3. **无任何自校验**：面数没变也照样导出、照样打印 "exported"。本版加了三道闸：
   三角面无下降 → NO_TRI_REDUCTION；超教训26 阈值 → REJECT_*；
   落盘面数 ≠ 减面后面数 → EXPORT_MISMATCH。三种情况都不留可信产物。
4. `angle_limit` 写死 5° 且两件共用；本版按件给角度（实测扫描确定）。
5. 既有产物面数与本次结果不符时**默认拒绝覆盖**（P02 已用于打 G3p-DEC 盘），需 --force。

本版做法
--------
- 每件独立 angle_limit，取值由实测角度扫描确定（见 JOBS 注释）。
- 验收阈值（教训26）：|体积差| < 0.3% 且 bbox 逐位不变（容差 1e-4 mm）。
- 结果写 `production/decimate-audit.json`，让"减了多少"有据可查。

用法（Blender 无头）
  blender -b --python tools/decimate_planar.py -- [--only P04] [--dry-run] [--force]
"""
import bpy
import bmesh
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSTL = ROOT / "candidate-stl"
OUT = ROOT / "plates-merged" / "decimated"
PROD = ROOT / "production"

# 每件的角度上限（度）。数值由 2026-10-16 实测角度扫描确定，不是推算。
# 扫描时记录的是 len(bm.faces)（n-gon 数），故下表 P04 的"1266"是**多边形数**，
# 其 STL 三角面数始终 4896 不变（见模块 docstring 第 1 条）。P02 的数字是真实三角面减少。
#   P02: 0.5°→7104 / 1.0°→6197 / 1.5°→5231(dVol .0775%) / 3.0°→1957 / 5.0°→1197(dVol 1.42%,dBbox .088 超差)
#   P04: 5.0°→1266 n-gon(三角面仍 4896,dVol .0002%,dBbox 0) / 5.7°+→1116 n-gon(dBbox .082 超差)
JOBS = {
    "P02": {"stl": "P02_BASE_LID_UNVERIFIED.stl", "angle_deg": 1.5,
            "why": "平面件；5° 时体积 -1.42%/外形缩 0.088mm 超差，1.5° 通过（教训26 阈值）"},
    "P04": {"stl": "P04_DRIVER_32T_UNVERIFIED.stl", "angle_deg": 5.0,
            "why": "预期判 NO_TRI_REDUCTION：DISSOLVE 只并 n-gon，STL 三角面不减。"
                   "保留此条是为了让该结论每次可复现，不是为产出可用减面件"},
}

VOL_TOL = 0.003      # |ΔV|/V < 0.3%
BBOX_TOL = 1e-4      # bbox 逐位不变（mm）


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only, dry, force = None, False, False
    i = 0
    while i < len(argv):
        if argv[i] == "--only" and i + 1 < len(argv):
            only = argv[i + 1]
            i += 2
        elif argv[i] == "--dry-run":
            dry = True
            i += 1
        elif argv[i] == "--force":
            force = True
            i += 1
        else:
            i += 1
    return only, dry, force


def stl_face_count(path):
    import struct
    d = Path(path).read_bytes()
    if len(d) < 84:
        return None
    return struct.unpack_from("<I", d, 80)[0]


def mesh_stats(obj):
    """评估后的**三角面数** / 多边形数 / 体积 / bbox（世界轴对齐，mm）。

    必须同时报两个面数（2026-10-16 踩的坑）：
    DECIMATE/DISSOLVE 把共面三角形合并成 n-gon，`len(bm.faces)` 因此大幅下降
    （P04: 4896→1266），但 **STL 只能存三角形**，n-gon 重新三角化后仍是 4896。
    拿"多边形数"去比"STL 三角面数"是量纲错误 —— HANDOFF 记的
    "P04 4896→1266（5°，vol 0.000%）"正是这个错误，导致以为减面生效、实则 no-op。
    真正能减少 STL 三角面的，只有合并掉**内部顶点/内部边**的那部分。
    """
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ev.matrix_world)
    npoly = len(bm.faces)
    try:
        vol = bm.calc_volume(signed=True)
    except Exception:
        vol = float("nan")
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    bb = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)] if xs else [0] * 6
    nvert = len(bm.verts)
    # 三角化后再数 —— 这才是 STL 里会出现的面数
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    ntri = len(bm.faces)
    bm.free()
    ev.to_mesh_clear()
    return ntri, npoly, nvert, float(vol), [float(x) for x in bb]


def write_stl_from_evaluated(obj, dst):
    """从**求值后**网格（含修改器效果）手写二进制 STL，返回面数。

    为什么不用 bpy.ops.wm.stl_export：它写的是 obj.data 原始网格。若
    modifier_apply 因上下文原因未真正生效，导出会得到**未减面**的原件，
    而 evaluated_get() 仍报减面后的面数 —— 这正是旧脚本"假减面入仓"的机制。
    写法与 finalize_exports.py 一致（80 字节头 + uint32 面数 + 50 字节/面）。
    """
    import struct
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(ev.matrix_world)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.verts.index_update()
    bm.faces.index_update()
    n = len(bm.faces)
    with open(dst, "wb") as fh:
        fh.write(b"EFFMEET2 V6 DECIMATED CANDIDATE NOT RELEASED MM".ljust(80, b" "))
        fh.write(struct.pack("<I", n))
        for f in bm.faces:
            p = [v.co for v in f.verts]
            nrm = f.normal
            fh.write(struct.pack("<12fH",
                                 nrm.x, nrm.y, nrm.z,
                                 p[0].x, p[0].y, p[0].z,
                                 p[1].x, p[1].y, p[1].z,
                                 p[2].x, p[2].y, p[2].z, 0))
    bm.free()
    ev.to_mesh_clear()
    return n


def run_one(pid, spec, dry, force=False):
    src = CSTL / spec["stl"]
    if not src.exists():
        return {"id": pid, "status": "MISSING_SOURCE", "stl": str(src)}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=str(src))
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj

    t0, p0, vt0, v0, bb0 = mesh_stats(obj)

    m = obj.modifiers.new("planar", "DECIMATE")
    m.decimate_type = "DISSOLVE"
    m.angle_limit = math.radians(spec["angle_deg"])
    m.delimit = {"NORMAL", "UV", "SEAM", "SHARP"}
    bpy.ops.object.modifier_apply(modifier=m.name)

    t1, p1, vt1, v1, bb1 = mesh_stats(obj)

    dbbox = max(abs(a - b) for a, b in zip(bb0, bb1))
    dvol = abs(v1 - v0) / abs(v0) if v0 else float("inf")

    rec = {
        "id": pid, "stl": spec["stl"], "angle_deg": spec["angle_deg"],
        "why": spec["why"],
        # tris_* 才是 STL 里真实存在的面数；polys_* 是 n-gon 数，导出即丢失
        "tris_before": t0, "tris_after": t1, "tris_removed": t0 - t1,
        "tris_reduction_pct": round(100.0 * (t0 - t1) / t0, 2) if t0 else 0.0,
        "polys_before": p0, "polys_after": p1,
        "verts_before": vt0, "verts_after": vt1,
        "volume_before": round(v0, 4), "volume_after": round(v1, 4),
        "volume_delta_pct": round(100.0 * dvol, 4),
        "bbox_before": [round(x, 4) for x in bb0],
        "bbox_after": [round(x, 4) for x in bb1],
        "bbox_max_delta_mm": round(dbbox, 6),
    }

    # ---- 判定：以 STL 三角面数为准，不以 n-gon 数为准 ----
    if t1 >= t0:
        rec["status"] = "NO_TRI_REDUCTION"
        rec["detail"] = (
            f"angle_limit={spec['angle_deg']}° 把多边形数从 {p0} 降到 {p1}，"
            f"但**三角面数 {t0}→{t1} 没有减少**。DISSOLVE 只是把共面三角形并成 n-gon，"
            f"STL 只存三角形，导出后重新三角化又变回原数量 —— 对切片器而言是 no-op。"
            f"要真正减少 STL 三角面，须用能删内部顶点的方式（如 DECIMATE/COLLAPSE "
            f"或 remesh），并重新过教训26 阈值")
    elif dvol >= VOL_TOL:
        rec["status"] = "REJECT_VOLUME"
        rec["detail"] = f"体积差 {100*dvol:.3f}% ≥ 阈值 {100*VOL_TOL:.1f}%（教训26）"
    elif dbbox > BBOX_TOL:
        rec["status"] = "REJECT_BBOX"
        rec["detail"] = f"bbox 变动 {dbbox:.6f}mm > {BBOX_TOL}（外形被削）"
    else:
        rec["status"] = "PASS_THRESHOLD"
        rec["detail"] = (f"STL 三角面 {t0}→{t1}（-{rec['tris_reduction_pct']}%），"
                         f"体积/bbox 在教训26 阈值内")

    # ---- 导出：只有过阈值才落盘，避免假减面入仓 ----
    rec["exported"] = None
    if dry:
        rec["note"] = "dry-run，未导出"
    elif rec["status"] != "PASS_THRESHOLD":
        rec["note"] = f"未过阈值（{rec['status']}），不导出"
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        dst = OUT / f"{pid}_decimated.stl"
        if dst.exists():
            old_n = stl_face_count(dst)
            rec["existing_faces"] = old_n
            if old_n != t1 and not force:
                rec["status"] = "CONFLICT_EXISTING"
                rec["detail"] = (f"既有产物 {dst.name} 是 {old_n} 面，本次 {spec['angle_deg']}° "
                                 f"产出 {t1} 面，不一致。该文件可能已用于打印，"
                                 f"默认不覆盖；确认要替换请加 --force")
                rec["note"] = "拒绝覆盖既有产物"
        if rec["status"] == "PASS_THRESHOLD":
            wrote = write_stl_from_evaluated(obj, dst)
            back = stl_face_count(dst)
            rec["exported"] = str(dst.relative_to(ROOT))
            rec["exported_bytes"] = dst.stat().st_size
            rec["exported_faces"] = back
            # 硬校验：落盘三角面数必须等于减面后三角面数，否则就是又一次"假减面"
            if back != t1 or wrote != t1:
                rec["status"] = "EXPORT_MISMATCH"
                rec["detail"] = (f"导出三角面数 {back}（写入 {wrote}）≠ 减面后 {t1}；"
                                 f"产物不可信，请检查导出路径")

    bpy.data.objects.remove(obj, do_unlink=True)
    return rec


def main():
    only, dry, force = parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)
    results = []
    for pid, spec in JOBS.items():
        if only and pid != only:
            continue
        print(f"[decimate] {pid}  angle={spec['angle_deg']}°  {spec['stl']}", flush=True)
        rec = run_one(pid, spec, dry, force)
        print(f"           STL三角面 {rec.get('tris_before')} -> {rec.get('tris_after')} "
              f"({rec.get('tris_reduction_pct')}%)   n-gon {rec.get('polys_before')} -> "
              f"{rec.get('polys_after')}   dVol={rec.get('volume_delta_pct')}%  "
              f"dBbox={rec.get('bbox_max_delta_mm')}mm  => {rec.get('status')}", flush=True)
        if rec.get("detail"):
            print(f"           {rec['detail']}", flush=True)
        results.append(rec)

    audit = {
        "scope": "planar-dissolve decimation with self-check; NOT a slicer or print result",
        "thresholds": {"volume_delta_pct_max": 100 * VOL_TOL, "bbox_delta_mm_max": BBOX_TOL},
        "dry_run": dry,
        "jobs": results,
    }
    if not dry:
        (PROD / "decimate-audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[decimate] audit -> {PROD/'decimate-audit.json'}", flush=True)

    bad = [r["id"] for r in results if r["status"] != "PASS_THRESHOLD"]
    print("DECIMATE_DONE", "ok" if not bad else f"NOT_OK:{','.join(bad)}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
