"""Extract blocked evaluated export meshes to ignored local diagnostics, not printable files."""
import bpy,bmesh,json,hashlib
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parent;LOCAL=ROOT.parents[1]/'local-only';bpy.context.window.scene=bpy.data.scenes['N5_PRINT_SPLIT_CANDIDATE'];dg=bpy.context.evaluated_depsgraph_get();rows=json.loads((ROOT/'parts.json').read_text(encoding='utf8'))['parts'];out={}
for r in rows:
 o=bpy.data.objects[r['object']];e=o.evaluated_get(dg);me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me);bm.transform(e.matrix_world);bm.transform(Matrix.Scale(1000,4));e.to_mesh_clear();bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.index_update();bm.faces.index_update();out[r['id']]={'vertices':[[float(c) for c in v.co] for v in bm.verts],'triangles':[[v.index for v in f.verts] for f in bm.faces]};bm.free()
(LOCAL/'v5-native-export-meshes.json').write_text(json.dumps({'input_model_sha256':hashlib.sha256((ROOT/'EffMeet2_NOMI_布局A_v5_拆件候选.blend').read_bytes()).hexdigest(),'meshes':out},separators=(',',':')),encoding='utf8');print('EXTRACTED',list(out),flush=True)
