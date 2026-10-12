"""Official independent mesh validator against actual final binary STL bytes, disposable scene only."""
import bpy,json,struct,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('validator',Path.home()/'.codex/skills/blender-geometry-validation/scripts/validate_scene.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
results=[]
for row in json.loads((ROOT/'parts.json').read_text(encoding='utf8'))['parts']:
 p=ROOT/row['stl'];b=p.read_bytes();n=struct.unpack_from('<I',b,80)[0];verts=[];faces=[];indices={}
 for i in range(n):
  values=struct.unpack_from('<12fH',b,84+i*50);tri=[]
  for k in range(3):
   point=tuple(values[3+k*3:6+k*3])
   if point not in indices:indices[point]=len(verts);verts.append(tuple(x*.001 for x in point))
   tri.append(indices[point])
  faces.append(tri)
 me=bpy.data.meshes.new(row['id']);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('STL_QA_'+row['id'],me);bpy.context.scene.collection.objects.link(o);bpy.context.view_layer.update();metrics,issues=v._mesh_metrics(o,False);results.append({'id':row['id'],'issues':issues,'metrics':metrics});bpy.data.objects.remove(o,do_unlink=True);bpy.data.meshes.remove(me)
(ROOT/'production/final-stl-independent-audit.json').write_text(json.dumps({'status':'WARN' if any(r['issues'] for r in results) else 'PASS','scope':'final binary STL geometry only, no print/hardware release','parts':results},indent=2),encoding='utf8');print('INDEPENDENT_STL',len(results),'issues',sum(bool(r['issues']) for r in results),flush=True)
