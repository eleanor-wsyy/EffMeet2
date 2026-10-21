# -*- coding: utf-8 -*-
"""List all objects in the v6 blend by collection; measure P13/P12 relationship."""
import bpy, math, json
from mathutils import Vector

BLEND = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6\EffMeet2_NOMI_布局A_v6_紧凑候选.blend"
OUT = {}

# open blend
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
OUT['scenes'] = [s.name for s in bpy.data.scenes]
OUT['active_scene'] = scene.name

objs = []
for o in scene.objects:
    colls = [c.name for c in o.users_collection]
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs=[v.x for v in bb]; ys=[v.y for v in bb]; zs=[v.z for v in bb]
    objs.append({
        'name': o.name, 'type': o.type, 'colls': colls,
        'loc': [round(v,4) for v in o.location],
        'bbox_mm': [[round(min(xs)*1000,1), round(min(ys)*1000,1), round(min(zs)*1000,1)],
                    [round(max(xs)*1000,1), round(max(ys)*1000,1), round(max(zs)*1000,1)]],
        'hide_render': o.hide_render,
        'parent': o.parent.name if o.parent else None,
    })
OUT['object_count'] = len(objs)
OUT['objects'] = objs

# collections summary
from collections import Counter
OUT['by_collection'] = {'|'.join(k): v for k, v in Counter(tuple(o['colls']) for o in objs).items()}

# ---- P13 / P12 detailed measurement ----
def find(name):
    return bpy.data.objects.get(name)

def eval_bbox_mm(o):
    dg = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(dg)
    me = e.to_mesh()
    xs=[];ys=[];zs=[]
    mw = e.matrix_world
    n = len(me.vertices)
    for v in me.vertices:
        co = mw @ v.co
        xs.append(co.x); ys.append(co.y); zs.append(co.z)
    e.to_mesh_clear()
    return (min(xs),min(ys),min(zs)),(max(xs),max(ys),max(zs)), n

meas = {}
for key, name in [('P13','N6_YAW_STOP_ARM'), ('P12','N6_SHAFT_LOWER_LOCK_COLLAR'),
                  ('P11','N6_HOLLOW_LOAD_SHAFT'), ('P03','N6_DRIVEN_64T')]:
    o = find(name)
    if not o:
        meas[key] = None; continue
    mn,mx,_ = eval_bbox_mm(o)
    meas[key] = {'name': name,
                 'bbox_min_mm': [round(v*1000,2) for v in mn],
                 'bbox_max_mm': [round(v*1000,2) for v in mx],
                 'z_range': [round(mn[2]*1000,2), round(mx[2]*1000,2)]}

# detailed: for P13 collect hole-like features from modifiers and mesh
p13 = find('N6_YAW_STOP_ARM')
p12 = find('N6_SHAFT_LOWER_LOCK_COLLAR')
p11 = find('N6_HOLLOW_LOAD_SHAFT')
feat = {}
if p13:
    feat['P13_modifiers'] = [(m.name, m.type, getattr(m,'operation',None)) for m in p13.modifiers]
    # evaluated mesh: find cylindrical faces (holes) via edge loops — sample vertex radii around Z
    dg = bpy.context.evaluated_depsgraph_get(); e = p13.evaluated_get(dg); me = e.to_mesh()
    mw = e.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    # radius histogram around Z axis at center (0,0) — shaft is on Z axis
    rs = sorted(set(round(math.hypot(v.x*1000, v.y*1000),1) for v in verts))
    feat['P13_radii_mm'] = rs[:20]
    feat['P13_vert_count'] = len(verts)
    feat['P13_face_count'] = len(me.polygons)
    # z levels of vertices
    zlev = sorted(set(round(v.z*1000,1) for v in verts))
    feat['P13_z_levels'] = zlev
    e.to_mesh_clear()
if p12:
    feat['P12_modifiers'] = [(m.name, m.type, getattr(m,'operation',None)) for m in p12.modifiers]
    dg = bpy.context.evaluated_depsgraph_get(); e = p12.evaluated_get(dg); me = e.to_mesh()
    mw = e.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    rs = sorted(set(round(math.hypot(v.x*1000, v.y*1000),1) for v in verts))
    feat['P12_radii_mm'] = rs[:24]
    zlev = sorted(set(round(v.z*1000,1) for v in verts))
    feat['P12_z_levels'] = zlev
    # find the pinch-screw hole axis: vertices near y=-21mm
    hole_pts = [v for v in verts if abs(v.y*1000 + 21) < 3 and abs(v.z*1000 - 28.25) < 4]
    if hole_pts:
        feat['P12_pinch_region_x_extent'] = [round(min(v.x for v in hole_pts)*1000,2), round(max(v.x for v in hole_pts)*1000,2)]
        # radius around the hole axis (y0=-21mm, z0=28.25mm) in YZ? hole along X: radius = hypot(y-y0, z-z0)
        hrs = sorted(set(round(math.hypot(v.y*1000+21, v.z*1000-28.25),2) for v in hole_pts))
        feat['P12_pinch_hole_radii'] = hrs[:12]
    e.to_mesh_clear()
# P11 D-flat positions: check x extent at various z bands
if p11:
    dg = bpy.context.evaluated_depsgraph_get(); e = p11.evaluated_get(dg); me = e.to_mesh()
    mw = e.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    bands = {}
    for z0,z1,label in [(26,33,'P12_band'),(42,51,'DRIVE_D_band'),(61,64,'P13_band'),(64,86,'upper')]:
        sel = [v for v in verts if z0-0.5 <= v.z*1000 <= z1+0.5]
        if sel:
            bands[label] = {'xmin':round(min(v.x for v in sel)*1000,2),'xmax':round(max(v.x for v in sel)*1000,2),
                            'rmin':round(min(math.hypot(v.x,v.y) for v in sel)*1000,2),
                            'rmax':round(max(math.hypot(v.x,v.y) for v in sel)*1000,2)}
    feat['P11_bands'] = bands
    e.to_mesh_clear()

OUT['measure_P13_P12'] = {'bboxes': meas, 'features': feat}
# also check for any object with 'SCREW'/'BOLT'/'M3' in name (bolt proxies)
OUT['bolt_like'] = [o.name for o in scene.objects if any(k in o.name.upper() for k in ('SCREW','BOLT','M3','M2'))]

import io, os
path = os.path.join(os.path.dirname(bpy.data.filepath), 'tools', 'inspect_result.json')
with io.open(path,'w',encoding='utf-8') as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1, default=str)
print('INSPECT_DONE', path)
print('OBJCOUNT', len(objs))
