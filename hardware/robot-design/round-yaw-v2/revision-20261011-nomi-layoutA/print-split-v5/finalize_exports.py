"""Repair ONLY export copies using Manifold3D. Native Blender source remains byte-identical.
Run after Blender extraction. Dependency manifold3d3.5.4+numpy, never commit wheel/cache.
"""
from pathlib import Path
import os,sys,json,hashlib,math,struct
import numpy as np
ROOT=Path(__file__).resolve().parent;LOCAL=ROOT.parents[1]/'local-only';sys.path.insert(0,os.environ.get('EFFMEET_MESH_TOOLS',str(LOCAL/'mesh-tools')))
import manifold3d as md
rowsdoc=json.loads((ROOT/'parts.json').read_text(encoding='utf8'));rows=rowsdoc['parts'];raw=json.loads((LOCAL/'v5-native-export-meshes.json').read_text(encoding='utf8'));model=ROOT/'EffMeet2_NOMI_布局A_v5_拆件候选.blend';assert raw['input_model_sha256']==hashlib.sha256(model.read_bytes()).hexdigest()
audit=json.loads((ROOT/'production/mesh-audit.json').read_text(encoding='utf8'));reports=[]
for r in rows:
 if r['id'] not in raw['meshes']:continue
 q=raw['meshes'][r['id']];vv=np.asarray(q['vertices'],dtype=np.float64);ff=np.asarray(q['triangles'],dtype=np.uint64);mesh=md.Mesh64(vv,ff,tolerance=.0001);m=md.Manifold(mesh);report={'id':r['id'],'raw_status':str(m.status()),'trials':[]}
 if m.status()!=md.Error.NoError:
  mesh.merge();m=md.Manifold(mesh);report['merged_status']=str(m.status())
 assert m.status()==md.Error.NoError,(r['id'],report)
 result=None
 for tolerance in (.001,.005,.01):
  simplified=m.simplify(tolerance);new=simplified.to_mesh64();v=np.asarray(new.vert_properties)[:,:3].copy();f=np.asarray(new.tri_verts).copy();a=v[f[:,1]]-v[f[:,0]];b=v[f[:,2]]-v[f[:,0]];areas=np.linalg.norm(np.cross(a,b),axis=1)/2;edges={}
  for face in f:
   for x,y in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):key=tuple(sorted((int(x),int(y))));edges[key]=edges.get(key,0)+1
  bound_delta=max(float(np.abs(v.min(axis=0)-vv.min(axis=0)).max()),float(np.abs(v.max(axis=0)-vv.max(axis=0)).max()));volume_delta=abs(simplified.volume()-m.volume())/max(m.volume(),1)
  trial={'tolerance_mm':tolerance,'faces':len(f),'zero_area':int(np.sum(areas==0)),'micro_faces':int(np.sum((areas>0)&(areas<1e-8))),'minimum_area_mm2':float(areas.min()),'watertight':all(n==2 for n in edges.values()),'bounds_delta_mm':bound_delta,'relative_volume_delta':volume_delta};report['trials'].append(trial)
  if not trial['zero_area'] and not trial['micro_faces'] and trial['watertight'] and bound_delta<=.011 and volume_delta<.001:result=(v,f,trial,simplified.volume());break
 assert result is not None,report
 v,f,trial,volume=result
 # Apply the same provisional orientation then ground, consistent with main export convention.
 R=np.eye(3)
 for axis,deg in enumerate(r['orientation_euler_deg']):
  angle=math.radians(deg);c=math.cos(angle);s=math.sin(angle);rr=[np.array([[1,0,0],[0,c,-s],[0,s,c]]),np.array([[c,0,s],[0,1,0],[-s,0,c]]),np.array([[c,-s,0],[s,c,0],[0,0,1]])][axis];R=rr@R
 placed=v@R.T;placed-=placed.min(axis=0)
 quantization=[]
 for iteration in range(3):
  quant=placed.astype(np.float32).astype(np.float64);qm=md.Manifold(md.Mesh64(quant,np.asarray(f,dtype=np.uint64),tolerance=.0001));assert qm.status()==md.Error.NoError,(r['id'],str(qm.status()))
  qout=qm.simplify(.001).to_mesh64();placed=np.asarray(qout.vert_properties)[:,:3].copy();f=np.asarray(qout.tri_verts).copy();q32=placed.astype(np.float32);unique,inv=np.unique(q32,axis=0,return_inverse=True);fac=inv[f];collapsed=int(np.sum((fac[:,0]==fac[:,1])|(fac[:,1]==fac[:,2])|(fac[:,0]==fac[:,2])));ee={}
  for face in fac:
   for x,y in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):key=tuple(sorted((int(x),int(y))));ee[key]=ee.get(key,0)+1
  ok=collapsed==0 and all(n==2 for n in ee.values());quantization.append({'iteration':iteration,'collapsed_float32_faces':collapsed,'watertight_float32':ok})
  if ok:break
 assert ok,(r['id'],quantization)
 report['float32_export_checks']=quantization
 filename=r['id']+'_'+r['object'].removeprefix('N5_')+'_UNVERIFIED.stl';path=ROOT/'candidate-stl'/filename
 with path.open('wb') as file:
  file.write(b'EFFMEET2 V5 CANDIDATE NOT RELEASED MM'.ljust(80,b' '));file.write(struct.pack('<I',len(f)))
  for face in f:
   tri=placed[face];normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=np.linalg.norm(normal);file.write(struct.pack('<12fH',*normal,*tri.ravel(),0))
 r.update({'mesh_status':'GEOMETRY_ONLY_PASS','release_status':'CANDIDATE_NOT_RELEASED','stl':'candidate-stl/'+filename,'stl_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'print_size_mm':[float(x) for x in placed.max(axis=0)],'export_cleanup':'Manifold3D3.5.4, maximum library simplification tolerance '+str(trial['tolerance_mm'])+'mm; native mesh untouched'})
 record=next(a for a in audit['parts'] if a['id']==r['id']);record['initial_blocking']=record['blocking'];record['blocking']=[];record['export_copy_repair']=report;record['final_export_volume_mm3']=volume;reports.append(report)
 print('FINALIZED',r['id'],trial,flush=True)
audit['all_closed']=all(not r['blocking'] for r in audit['parts']);audit['cleanup_note']='Initial Blender mesh diagnostics retained; final repaired copies checked separately. Does NOT authorize printing.'
(ROOT/'production/mesh-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8');(ROOT/'parts.json').write_text(json.dumps(rowsdoc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(ROOT/'production/export-repair-report.json').write_text(json.dumps({'status':'PASS','input_model_sha256':raw['input_model_sha256'],'native_model_unchanged':hashlib.sha256(model.read_bytes()).hexdigest()==raw['input_model_sha256'],'library':'manifold3d3.5.4','scope':'candidate export mesh only, no release','parts':reports},indent=2),encoding='utf8')
binding=json.loads((ROOT/'production/source-binding.json').read_text());binding['export_finalize_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();binding['extract_source_sha256']=hashlib.sha256((ROOT/'extract_export_meshes.py').read_bytes()).hexdigest();(ROOT/'production/source-binding.json').write_text(json.dumps(binding,indent=2),encoding='utf8')
