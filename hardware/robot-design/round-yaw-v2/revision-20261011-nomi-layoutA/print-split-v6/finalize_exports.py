"""v6: manifold3d-checked candidate STL export from extracted evaluated meshes. Native blend untouched.
Run (system python, after extract_export_meshes.py): python finalize_exports.py
"""
from pathlib import Path
import os,sys,json,hashlib,math,struct,csv
import numpy as np
ROOT=Path(__file__).resolve().parent;LOCAL=ROOT/'local-only';OUT=ROOT/'candidate-stl';PROD=ROOT/'production';OUT.mkdir(exist_ok=True)
sys.path.insert(0,os.environ.get('EFFMEET_MESH_TOOLS',str(LOCAL/'mesh-tools')))
import manifold3d as md
seed=json.loads((PROD/'parts-seed.json').read_text(encoding='utf8'));raw=json.loads((LOCAL/'v6-native-export-meshes.json').read_text(encoding='utf8'))
model=ROOT/'EffMeet2_NOMI_布局A_v6_紧凑候选.blend';assert raw['input_model_sha256']==hashlib.sha256(model.read_bytes()).hexdigest(),'blend changed after extract'
GREY={'N6_HEAD_SHELL','N6_BASE_CUP','N6_BASE_LID'};BED=256
# start orientation (deg XYZ) + support hint; Y-axis cylindrical/face parts lie flat with front down.
ORIENT={'N6_HEAD_SHELL':((90,0,0),'前圈朝下；内底/接收座局部支撑，须试切片'),'N6_FACE_PANEL':((90,0,0),'面朝平台；后柱向上'),
 'N6_BASE_CUP':((0,0,0),'底面朝下；肩部圆弧/声槽支撑待预览'),'N6_BASE_LID':((0,0,0),'接缝圈朝下；顶面悬空需树支撑'),
 'N6_LCD_REAR_CLAMP_FRAME':((90,0,0),'框面平放'),'N6_CAMERA_CRADLE':((90,0,0),'镜头管朝平台'),'N6_CAMERA_BACK_PLATE':((-90,0,0),'板面平放；压筋/FPC槽向上，无支撑'),'N6_PRIVACY_GUIDE':((90,0,0),'平放，导槽向上'),
 'N6_PRIVACY_BLADE':((90,0,0),'平放；拨片局部支撑'),'N6_SPEAKER_CRADLE':((90,0,0),'圆筒轴竖直；腿部支撑待预览'),
 'N6_MIC_RETAINER_-1':((90,0,0),'平放，无支撑'),'N6_MIC_RETAINER_1':((90,0,0),'平放，无支撑'),'N6_STOP_KEY_CAP':((180,0,0),'键面朝平台')}
def rot(deg):
 R=np.eye(3)
 for ax,dd in enumerate(deg):
  a=math.radians(dd);c,s=math.cos(a),math.sin(a);R=[np.array([[1,0,0],[0,c,-s],[0,s,c]]),np.array([[c,0,s],[0,1,0],[-s,0,c]]),np.array([[c,-s,0],[s,c,0],[0,0,1]])][ax]@R
 return R
def edge_ok(f):
 e={}
 for t in f:
  for x,y in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):k=(min(x,y),max(x,y));e[k]=e.get(k,0)+1
 return all(n==2 for n in e.values())
def read_back(path):
 data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n
 vs={};f=[];vol=0.0;zero=0
 for i in range(n):
  q=struct.unpack_from('<12fH',data,84+50*i);tri=[];P=[]
  for j in range(3):
   p=q[3+3*j:6+3*j];tri.append(vs.setdefault(p,len(vs)));P.append(np.array(p,dtype=np.float64))
  f.append(tri);c=np.cross(P[1]-P[0],P[2]-P[0]);zero+=int(not c.any());vol+=float(np.dot(P[0],np.cross(P[1],P[2])))/6
 return {'triangles':n,'watertight':edge_ok(f) and len({tuple(sorted(t)) for t in f})==n,'collapsed':sum(len(set(t))<3 for t in f),'zero_area':zero,'signed_volume_mm3':round(vol,2)}
rows=[];audit=[]
for p in seed['parts']:
 q=raw['meshes'][p['id']];vv=np.asarray(q['vertices'],dtype=np.float64);ff=np.asarray(q['triangles'],dtype=np.uint64)
 mesh=md.Mesh64(vv,ff,tolerance=.0001);m=md.Manifold(mesh);st=str(m.status())
 if m.status()!=md.Error.NoError:mesh.merge();m=md.Manifold(mesh)
 assert m.status()==md.Error.NoError,(p['id'],st)
 deg,sup=ORIENT.get(p['object'],((0,0,0),'底面朝下；局部支撑待切片'))
 out=m.simplify(.001).to_mesh64();v=np.asarray(out.vert_properties)[:,:3].copy()@rot(deg).T;f=np.asarray(out.tri_verts).copy();v-=v.min(axis=0)
 for it in range(3):
  q32=v.astype(np.float32).astype(np.float64);qm=md.Manifold(md.Mesh64(q32,f.astype(np.uint64),tolerance=.0001));assert qm.status()==md.Error.NoError,p['id']
  o2=qm.to_mesh64();v=np.asarray(o2.vert_properties)[:,:3].astype(np.float32).astype(np.float64);f=np.asarray(o2.tri_verts).copy()
  u,inv=np.unique(v.astype(np.float32),axis=0,return_inverse=True);fac=inv.reshape(-1)[f]
  if not np.any((fac[:,0]==fac[:,1])|(fac[:,1]==fac[:,2])|(fac[:,0]==fac[:,2])) and edge_ok(fac.tolist()):break
 name=p['object'].removeprefix('N6_');fn=f"{p['id']}_{name}_UNVERIFIED.stl";path=OUT/fn
 with path.open('wb') as fh:
  fh.write(b'EFFMEET2 V6 CANDIDATE NOT RELEASED MM'.ljust(80,b' '));fh.write(struct.pack('<I',len(f)))
  for t in f:
   tri=v[t];nrm=np.cross(tri[1]-tri[0],tri[2]-tri[0]);ln=np.linalg.norm(nrm);nrm=nrm/ln if ln else nrm;fh.write(struct.pack('<12fH',*nrm,*tri.ravel(),0))
 rb=read_back(path);rb.update({'id':p['id'],'stl':fn,'manifold_volume_mm3':round(qm.volume(),2)});audit.append(rb)
 size=[round(float(x),2) for x in v.max(axis=0)];grey=p['object'] in GREY
 rows.append({'id':p['id'],'name':p['name'],'object':p['object'],'quantity':1,'material':'PLA Matte','color':'灰' if grey else '黑','interface_status':'unverified','size_mm':size,
  'orientation_start_euler_deg':list(deg),'support_start':sup,'plate_start':'GREY' if grey else 'BLACK','fits_256_bed':all(x<=BED-16 for x in size[:2]) and size[2]<=BED,
  'rotating_with_head':p['rotating'],'stl':'candidate-stl/'+fn,'stl_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'slicer_status':'NOT_RUN','sample_print_status':'NOT_RUN','release_status':'CANDIDATE_NOT_RELEASED'})
 print('EXPORTED',fn,size,rb['watertight'],rb['signed_volume_mm3'],flush=True)
ok=all(a['watertight'] and a['signed_volume_mm3']>0 and not a['collapsed'] and not a['zero_area'] for a in audit)
(PROD/'export-byte-audit.json').write_text(json.dumps({'status':'PASS' if ok else 'FAIL','count':len(audit),'scope':'re-read float32 binary STL bytes; candidate only','parts':audit},indent=1),encoding='utf8')
doc={'revision':'v6','layout':'A2','status':'conditional_candidate','units':'mm','stage':'reversible_blockout','manufacturing_ready':False,'hardware_validated':False,'plates_frozen':False,'model_sha256':raw['input_model_sha256'],'parts':rows}
(ROOT/'parts.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
cols=['id','name','quantity','material','color','interface_status','size_mm','orientation_start_euler_deg','support_start','plate_start','fits_256_bed','stl','slicer_status','sample_print_status','release_status']
with (ROOT/'PARTS.csv').open('w',encoding='utf-8-sig',newline='') as fh:
 w=csv.writer(fh);w.writerow(cols)
 for r in rows:w.writerow(['×'.join(str(x) for x in r[c]) if isinstance(r[c],list) else r[c] for c in cols])
print('FINALIZE',doc['revision'],len(rows),'byte_audit',ok,'bed_fail',[r['id'] for r in rows if not r['fits_256_bed']],flush=True)
