"""v6: extract evaluated printed-part meshes (mm, world pose) to local-only JSON. Proxies/keep-outs excluded."""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parent;LOCAL=ROOT/'local-only';LOCAL.mkdir(exist_ok=True)
seed=json.loads((ROOT/'production/parts-seed.json').read_text(encoding='utf8'));bpy.context.window.scene=bpy.data.scenes[seed['scene']]
dg=bpy.context.evaluated_depsgraph_get();out={}
for r in seed['parts']:
 o=bpy.data.objects[r['object']];assert o.users_collection[0].name=='N6_PRINTED_PARTS',r
 e=o.evaluated_get(dg);me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me);bm.transform(e.matrix_world);bm.transform(Matrix.Scale(1000,4));e.to_mesh_clear()
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update()
 out[r['id']]={'vertices':[[float(c) for c in v.co] for v in bm.verts],'triangles':[[v.index for v in f.verts] for f in bm.faces]};bm.free()
blend=ROOT/'EffMeet2_NOMI_布局A_v6_紧凑候选.blend'
(LOCAL/'v6-native-export-meshes.json').write_text(json.dumps({'input_model_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'meshes':out},separators=(',',':')),encoding='utf8')
print('EXTRACTED',len(out),flush=True)
