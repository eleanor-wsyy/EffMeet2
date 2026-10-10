import bpy,bmesh,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
scene=bpy.data.scenes['R2_ROUND_YAW_BLOCKOUT'];bpy.context.window.scene=scene
head=bpy.data.objects['R2_HEAD_SHELL'];yaw=bpy.data.objects['R2_HEAD_YAW_POSE'];rows=[]
for fr,deg in [(1,-45),(31,0),(61,45)]:
    scene.frame_set(fr);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=head.evaluated_get(dg);me=ev.to_mesh();bm=bmesh.new();bm.from_mesh(me)
    dep=[]
    for m in head.modifiers:
        if m.type=='BOOLEAN' and m.object:
            dep.append({'cutter':m.object.name,'same_parent':m.object.parent==yaw})
    rows.append({'yaw_deg':deg,'closed_volume_mm3':abs(bm.calc_volume())*1e9,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'boolean_dependencies':dep})
    bm.free();ev.to_mesh_clear()
base=rows[1]['closed_volume_mm3'];variation=max(abs(r['closed_volume_mm3']-base)/base for r in rows)
passed=variation<.0001 and all(r['nonmanifold_edges']==0 and r['zero_area_faces']==0 and all(d['same_parent'] for d in r['boolean_dependencies']) for r in rows)
report={'scope':'native evaluated rotating shell at -45/0/+45; no physical drive/cable/torque test','status':'PASS' if passed else 'FAIL','maximum_volume_relative_change':variation,'threshold':.0001,'poses':rows}
(ROOT/'production'/'yaw-dependency-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if not passed:raise RuntimeError('Yaw dependency audit failed')
print('YAW_DEPENDENCY_PASS '+str(variation))
