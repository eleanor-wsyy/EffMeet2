"""Local face-retention R1 candidate; canonical v6/source/STLs are never overwritten."""
import bpy,bmesh,json,math,hashlib,struct
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT.parent.parent/'EffMeet2_NOMI_布局A_v6_紧凑候选.blend';CFG=json.loads((ROOT/'retention_config.json').read_text());U=.001
assert Path(bpy.data.filepath).resolve()==SOURCE.resolve()
source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest();scene=bpy.data.scenes['N6_COMPACT_CANDIDATE'];bpy.context.window.scene=scene;dg=bpy.context.evaluated_depsgraph_get()
PAR=json.loads((ROOT/'../../../../parameters.json').resolve().read_text(encoding='utf8'))
head=bpy.data.objects['N6_HEAD_SHELL'];face=bpy.data.objects['N6_FACE_PANEL'];HC=PAR['head']['center'][2];FY=PAR['head']['face_panel_center'][1];FT=2.4;FRONT=FY-FT/2;BACK=FY+FT/2
parts=list(bpy.data.collections['N6_PRINTED_PARTS'].objects);proxies=[o for o in bpy.data.collections['N6_COMPONENT_PROXIES'].objects if o.type=='MESH']
def mesh_world(o):
 dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);me=bpy.data.meshes.new_from_object(e);me.transform(e.matrix_world);return me

def bm_mm(o):
 me=mesh_world(o);bm=bmesh.new();bm.from_mesh(me);bpy.data.meshes.remove(me);bm.transform(Matrix.Scale(1000,4));bm.normal_update();return bm

def signature(o):
 m=mesh_world(o);h=hashlib.sha256();h.update(b''.join(struct.pack('<fff',*v.co) for v in m.vertices));h.update(b''.join(struct.pack('<I',i) for p in m.polygons for i in p.vertices));bpy.data.meshes.remove(m);return h.hexdigest()

def stats(bm):
 bm.verts.ensure_lookup_table();rem=set(v.index for v in bm.verts);count=0
 while rem:
  count+=1;stack=[rem.pop()]
  while stack:
   for edge in bm.verts[stack.pop()].link_edges:
    for v in edge.verts:
     if v.index in rem:rem.remove(v.index);stack.append(v.index)
 return {'vertices':len(bm.verts),'faces':len(bm.faces),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'components':count,'signed_volume_mm3':bm.calc_volume(signed=True),'zero_area_faces':sum(f.calc_area()<=1e-10 for f in bm.faces),'bbox_mm':[[min(v.co[i] for v in bm.verts) for i in range(3)],[max(v.co[i] for v in bm.verts) for i in range(3)]]}
before={o.name:signature(o) for o in parts};(ROOT/'production/source-before.json').write_text(json.dumps({'source_sha256':source_sha,'printed_parts':before},indent=2))
CUT=bpy.data.collections.new('R1_NATIVE_CONTROLS');scene.collection.children.link(CUT);FAST=bpy.data.collections.new('R1_PURCHASED_FASTENER_BUDGETS');scene.collection.children.link(FAST)
def move_col(o,c):
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o)
def cyl(name,d,h,center,verts=64,c=CUT):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=d*U/2,depth=h*U,location=Vector(center)*U,rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='R1_'+name;move_col(o,c)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.hide_render=c==CUT;o.hide_set(c==CUT);o['never_printed']=True;return o

def box(name,dim,center,rz=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)*U);o=bpy.context.object;o.name='R1_'+name;move_col(o,CUT);o.dimensions=Vector(dim)*U;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.rotation_euler.y=rz;o.hide_render=True;o.hide_set(True);o['never_printed']=True;return o

def boolean(host,cut,operation='DIFFERENCE'):
 mod=host.modifiers.new('R1 '+operation+' '+cut.name,'BOOLEAN');mod.operation=operation;mod.solver='MANIFOLD';mod.object=cut;return mod
anchors=[]
for i,(x,zrel) in enumerate(CFG['centers_xz_relative_head_mm'],1):
 z=HC+zrel;r=math.hypot(x,zrel);ux,uz=x/r,zrel/r;angle=math.atan2(uz,ux)
 receiver=cyl(f'RECEIVER_{i}',10,9,(x,BACK+4.5,z));boolean(head,receiver,'UNION')
 # Radial rib crosses the source receiving lip (r=53.3..57.2) and the receiver.
 rin=r-1.0;rout=55.2;rc=(rin+rout)/2
 bridge=box(f'LIP_BRIDGE_{i}',(rout-rin,3,6),(ux*rc,BACK+1.5,HC+uz*rc),rz=-angle);boolean(head,bridge,'UNION')
 boolean(head,cyl(f'HEAD_THROUGH_{i}',3.4,20,(x,BACK+4,z)))
 boolean(face,cyl(f'FACE_THROUGH_{i}',3.4,12,(x,FY,z)))
 nut_y=BACK+6.5
 pocket=cyl(f'CAPTIVE_NUT_POCKET_{i}',5.7/math.cos(math.pi/6),2.8,(x,nut_y,z),verts=6);boolean(head,pocket)
 slot=box(f'RADIAL_NUT_LOAD_SLOT_{i}',(8,2.8,6.8),(x-ux*3,nut_y,z-uz*3),rz=-angle);boolean(head,slot)
 cap=cyl(f'M3_CAP_{i}',5.5,3,(x,FRONT-1.5,z),c=FAST);cap.data.materials.append(bpy.data.materials['N6_PLA_BLACK_PREVIEW']);cap['scope']='purchased screw envelope, NOT supplier CAD';cap['never_printed']=True
 shank=cyl(f'M3_SHAFT_{i}',3,12,(x,FRONT+6,z),c=FAST);shank.data.materials.append(bpy.data.materials['N6_METAL_PROXY']);shank['scope']='screw thread omitted, envelope only'
 nut=cyl(f'M3_NUT_{i}',5.5/math.cos(math.pi/6),2.4,(x,nut_y,z),verts=6,c=FAST);boolean(nut,cyl(f'NUT_THREAD_CLEAR_{i}',3.1,5,(x,nut_y,z)));nut.data.materials.append(bpy.data.materials['N6_METAL_PROXY']);nut['scope']='purchased nut budget, no thread certification'
 for o in (cap,shank,nut):o['never_printed']=True;o['interface_status']='unverified'
 anchors.append({'id':i,'x_mm':x,'z_mm':z,'axis':'Y','panel_front_y':FRONT,'panel_back_y':BACK,'receiver_front_y':BACK,'receiver_back_y':BACK+9,'nut_center_y':nut_y,'screw_tip_y':FRONT+12,'nominal_thread_beyond_nut_mm':FRONT+12-(nut_y+1.2),'panel_to_receiver_gap_mm':0,'nut_side_loading':'radially from head interior; no glue load path'})
bpy.context.view_layer.update()
# No source part but the two declared shells may change.
after={o.name:signature(o) for o in parts};unrelated=[n for n in before if n not in (head.name,face.name) and before[n]!=after[n]]
report={'schema_version':'1.0','status':'pending','scope':'local geometry candidate only','source_sha256':source_sha,'changed_parts':[n for n in before if before[n]!=after[n]],'unexpected_changed_parts':unrelated,'anchors':anchors,'manufacturing_ready':False,'hardware_validated':False,'interfaces_unverified':['screw SKU/head envelope','nut SKU/AF/thickness','printed clearance and torque','LCD mounting measurements']}
T={}
for o in parts+proxies:
 bm=bm_mm(o);bi=bm.copy()
 for v in bi.verts:v.co-=v.normal*.05
 T[o.name]=(BVHTree.FromBMesh(bi),bm);bi.free()
report['modified_meshes']={o.name:stats(T[o.name][1]) for o in (head,face)}
report['surface_intersections']=[]
for a in (head.name,face.name):
 for b in T:
  if a==b or (a==face.name and b==head.name):continue
  hits=T[a][0].overlap(T[b][0])
  if hits:report['surface_intersections'].append({'a':a,'b':b,'triangle_pairs':len(hits)})
report['check_method']='same BVH surface inset 0.05mm as canonical v6; source envelopes budget-only; not a stress or tolerance analysis'
fail=bool(unrelated or report['surface_intersections']) or set(report['changed_parts'])!={head.name,face.name}
for st in report['modified_meshes'].values():fail|=bool(st['nonmanifold_edges'] or st['boundary_edges'] or st['components']!=1 or st['signed_volume_mm3']<=0 or st['zero_area_faces'])
report['status']='FAIL' if fail else 'PASS'
(ROOT/'production/geometry-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('R1_GEOMETRY',json.dumps(report,ensure_ascii=False),flush=True)
if fail:raise RuntimeError('R1 geometry review failed; no export or completion')
scene.name='N6_FACE_RETENTION_R1_CANDIDATE';scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
try:
 pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
 for d in pref.devices:d.use=d.type!='CPU'
 scene.cycles.device='GPU'
except Exception:pass
scene.camera=bpy.data.objects['N6_CAM_HERO'];scene.render.resolution_x=1500;scene.render.resolution_y=1125
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'EffMeet2_v6_面板三点固定_R1候选.blend'),compress=True)
scene.render.filepath=str(ROOT/'renders/01_assembled_candidate.png');bpy.ops.render.render(write_still=True)
# Exploded evidence must use fully evaluated copies, not moving native Boolean hosts alone.
import runpy
runpy.run_path(str(ROOT/'render_exploded_evaluated.py'),run_name='__r1_exploded__')
# Two changed mesh exports only, conditional replacement candidates, never canonical STL files.
D=ROOT/'candidate-stl-local';D.mkdir(exist_ok=True)
for o,fn in [(head,'HEAD_SHELL_R1_UNVERIFIED.stl'),(face,'FACE_PANEL_R1_UNVERIFIED.stl')]:
 bm=T[o.name][1].copy();bmesh.ops.triangulate(bm,faces=list(bm.faces));out=bytearray(b'R1 local candidate, not canonical or manufacturing released'.ljust(80,b' '));out+=struct.pack('<I',len(bm.faces))
 for f in bm.faces:
  vs=[v.co for v in f.verts];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized();out+=struct.pack('<12fH',*normal,*vs[0],*vs[1],*vs[2],0)
 (D/fn).write_bytes(out);bm.free()
for _,bm in T.values():bm.free()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_sha
(ROOT/'production/source-preservation.json').write_text(json.dumps({'status':'PASS','canonical_source_sha256':source_sha,'changed_original_source_file':False,'unrelated_printed_parts_changed':unrelated},indent=2),encoding='utf8')
print('R1_COMPLETE',flush=True)
