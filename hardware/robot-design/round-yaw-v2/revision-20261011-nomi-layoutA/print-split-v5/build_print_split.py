"""v5 conditional print split. Open v4 blend, clone scene; never apply native owners.
STLs are evaluated, cleaned candidate volumes, NOT manufacturing releases.
"""
import bpy,bmesh,json,math,struct,hashlib,importlib.util,os
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parent;REV=ROOT.parent;PARAM=REV.parent/'parameters.json';P=json.loads(PARAM.read_text(encoding='utf8'));S=P['print_split'];U=.001
PROD=ROOT/'production';OUT=ROOT/'candidate-stl';REN=ROOT/'renders'
for d in (PROD,OUT,REN):d.mkdir(exist_ok=True)
SK=Path.home()/'.codex/skills'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,str(p));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
snap=load('snap',SK/'blender-geometry-validation/scripts/snapshot_scene.py')
protected=sorted(o.name for o in bpy.data.objects);before=snap.capture_snapshot(protected)
source=bpy.data.scenes['N4_NOMI_LAYOUT_A_CANDIDATE'];scene=bpy.data.scenes.new('N5_PRINT_SPLIT_CANDIDATE');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
# Deep-copy objects/data; remap all modifier and parenting dependencies. Earlier scenes untouched.
cols={};objs={}
def clone_col(c,parent):
 n=bpy.data.collections.new(c.name.replace('N4_','N5_',1));parent.children.link(n);cols[c]=n
 for sub in c.children:clone_col(sub,n)
for c in source.collection.children:clone_col(c,scene.collection)
for old in source.objects:
 n=old.copy()
 if old.data:n.data=old.data.copy()
 n.name=old.name.replace('N4_','N5_',1);objs[old]=n
 for c in old.users_collection:
  if c in cols:cols[c].objects.link(n)
for old,n in objs.items():
 if old.parent:n.parent=objs.get(old.parent,old.parent);n.matrix_parent_inverse=old.matrix_parent_inverse.copy();n.matrix_basis=old.matrix_basis.copy()
 for mod in n.modifiers:
  for prop in ('object','offset_object','mirror_object'):
   if hasattr(mod,prop):
    target=getattr(mod,prop)
    if target in objs:setattr(mod,prop,objs[target])
 for con in n.constraints:
  if hasattr(con,'target') and con.target in objs:con.target=objs[con.target]
scene.world=source.world.copy();scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
C=bpy.data.collections.new('N5_REAL_CANDIDATE_PARTS');scene.collection.children.link(C)
CTRL=bpy.data.collections.new('N5_SPLIT_NATIVE_CONTROLS');scene.collection.children.link(CTRL)
GREY=bpy.data.materials['N4_PLA_GREY_PREVIEW'];BLACK=bpy.data.materials['N4_PLA_BLACK_PREVIEW'];yaw=bpy.data.objects['N5_YAW_LAYOUT_ANCHOR']
parts=[];helpers=[];sequence=0

def obj(n,verts,faces,center=(0,0,0),helper=True,mat=BLACK):
 me=bpy.data.meshes.new('N5_'+n+'_MESH');me.from_pydata([[v*U for v in p] for p in verts],[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();o=bpy.data.objects.new('N5_'+n,me);(CTRL if helper else C).objects.link(o);o.location=Vector(center)*U
 if mat:me.materials.append(mat)
 if helper:helpers.append(o);o.hide_render=True;o.hide_set(True)
 return o

def box(n,size,center,helper=True,mat=BLACK,bevel=0):
 x,y,z=[v/2 for v in size];v=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)];f=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 o=obj(n,v,f,center,helper,mat)
 if bevel:
  m=o.modifiers.new('Real edge radius','BEVEL');m.width=bevel*U;m.segments=3
 return o

def cylinder(n,d,h,center,axis='Z',helper=True,mat=BLACK,segments=96):
 r=d/2;v=[(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),z*h/2) for z in (-1,1) for i in range(segments)];f=[tuple(range(segments-1,-1,-1)),tuple(range(segments,2*segments))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
 o=obj(n,v,f,center,helper,mat)
 if axis=='Y':o.data.transform(Matrix.Rotation(math.pi/2,4,'X'))
 if axis=='X':o.data.transform(Matrix.Rotation(math.pi/2,4,'Y'))
 return o

def boolop(host,cut,op='DIFFERENCE'):
 m=host.modifiers.new(op+' '+cut.name,'BOOLEAN');m.operation=op;m.solver='MANIFOLD';m.object=cut;return m

def unite(host,piece):return boolop(host,piece,'UNION')
def hole(host,center,d=3.4,depth=250,axis='Z'):
 return boolop(host,cylinder(host.name+'_HOLE_'+str(len(host.modifiers)),d,depth,center,axis))
def ring(n,od,idd,h,center,axis='Z',helper=False):
 o=cylinder(n,od,h,center,axis,helper);hole(o,center,idd,h+4,axis);return o

def hexhole(host,center,flat=5.7,depth=2.6,axis='Z'):
 return boolop(host,cylinder(host.name+'_NUT_'+str(len(host.modifiers)),flat/math.cos(math.pi/6),depth,center,axis,segments=6))
def attach_yaw(o):
 if o.parent==yaw:return
 assert o.parent is None,'Unexpected parent on new control'
 # Anchor is at world origin at neutral yaw. Read basis directly, not stale matrix_world.
 basis=o.matrix_basis.copy();o.parent=yaw;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=basis

def part(o,cn,group='B3',orient=(0,0,0),support='局部支撑待切片',interface='unverified',motion=False,function='',thin=None):
 global sequence
 sequence+=1;pid=f'P{sequence:02d}'
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o);o.hide_render=False;o.hide_set(False)
 if motion:attach_yaw(o)
 o['part_id']=pid;o['interface_status']=interface;o['manufacturing_ready']=False;o['hardware_validated']=False;o['stage']='reversible_blockout'
 parts.append({'id':pid,'name':cn,'object':o.name,'quantity':1,'material':'PLA Matte','color':'灰' if group.startswith('G') else '黑','plate_group':group,'orientation_euler_deg':list(orient),'orientation_status':'NOT_SLICED_NOT_PRINTED','support_start':support,'interface_status':interface,'function':function or cn,'thin_exception_mm':thin,'object_ref':o})
 print('BUILT',pid,cn,flush=True);return o

def base_boss(x,y,top=8,diam=10,hole_d=3.4,captive=True):
 c=cylinder(f'CUP_BOSS_{x}_{y}',diam,top-4.2,(x,y,(top+4.2)/2));unite(cup,c);hole(cup,(x,y,8),hole_d,30)
 if captive:hexhole(cup,(x,y,3.2),5.7,3.0)
 return c
cup=bpy.data.objects['N5_BASE_CUP'];lid=bpy.data.objects['N5_BASE_LID'];head=bpy.data.objects['N5_HEAD_SHELL'];face=bpy.data.objects['N5_FACE_PANEL'];neck=bpy.data.objects['N5_SHORT_YAW_NECK']
for o in (cup,lid,head,face,neck):o['interface_status']='unverified'
# Replace all earlier moving/control proxies in the cloned scene; no proxy is exported.
for name in ('STOP_BUTTON_CAP_PROXY','PRIVACY_SLIDER_PROXY'):
 bpy.data.objects['N5_'+name].hide_render=True
for o in scene.objects:
 if 'SUPPORT_ENVELOPES' in str([c.name for c in o.users_collection]):o.hide_render=True
# Build first part table before evaluating/arranging plates.
part(head,'头壳（原生曲面＋新增接收）','G1',(90,0,0),'前圈朝下；内底/接收座局部支撑，必须试切片',motion=True)
part(face,'圆形黑面板','B1',(90,0,0),'面朝平台；后口袋向上，支撑待预览',motion=True)
part(neck,'短颈＋止转舌','B1',support='轴向孔竖直，肩台局部支撑',motion=True)
part(lid,'底座上盖＋机械限位','G3',support='接缝圈朝下；中心悬空和螺钉柱局部支撑')
part(cup,'底座杯体＋接收柱＋出音通道','G2',support='底面朝下；深柱/声学通道支撑待预览')
# Bearing tower: independent load path to cup, four full through-bolts; no servo load bearing.
bolt_xy=S['bearing']['stack_bolt_xy']
tower=box('BEARING_TOWER',(70,12,3.2),(0,0,11.6),False,bevel=.6)
for x in (-28,28):
 unite(tower,box('TOWER_FOOT_'+str(x),(14,38,3.2),(x,0,11.6)))
 for y in (-14,14):
  unite(tower,box(f'TOWER_COLUMN_{x}_{y}',(10,10,33.8),(x,y,27.9)))
  hole(tower,(x,y,30),3.4,60);base_boss(x,y,10,12,captive=False);hole(cup,(x,y,1.1),6.4,8.2)
part(tower,'双轴承承力塔','B2',support='脚面朝下；贯穿孔竖直；顶部接触面预览')
for upper,z in ((False,49.5),(True,69.5)):
 for right in (False,True):
  sign=1 if right else -1;label=('UPPER' if upper else 'LOWER')+('_RIGHT' if right else '_LEFT')
  seat=ring('BEARING_SEAT_'+label,54,S['bearing']['seat_bore'],9.4,(0,0,z))
  unite(seat,ring('BEARING_LIP_'+label,54,38.5,1,(0,0,z-4.2),helper=True))
  # SplitX clamp bolts run X atY+/-24; stack bolts remainZ atX+/-28,Y+/-14.
  # The two fastener systems cannot cross or share holes.
  for y in (-24,24):
   unite(seat,box('SEAT_CLAMP_BAR_'+label+str(y),(66,14,9.4),(0,y,z)))
   hole(seat,(0,y,z),3.4,90,'X')
  for x,y in bolt_xy:unite(seat,box('SEAT_STACK_EAR_'+label+str(x)+str(y),(12,14,9.4),(x,y,z)))
  hole(seat,(0,0,z+6.3),S['bearing']['seat_bore'],20);hole(seat,(0,0,z-4.2),38.5,1.2)
  boolop(seat,box('SEAT_SPLIT_'+label,(80,160,40),(-sign*40,0,z)))
  boolop(seat,box('SEAT_SPLIT_GAP_'+label,(.4,160,40),(0,0,z)))
  for y in (-14,14):
   hole(seat,(sign*28,y,z),3.4,40)
   if upper:hexhole(seat,(sign*28,y,z+3.2),5.9,3.4)
  if right:
   for y in (-24,24):hexhole(seat,(31.8,y,z),5.7,2.6,'X')
  part(seat,('上' if upper else '下')+'轴承座'+('右半' if right else '左半'),'B2',(0,-90*sign,0),'分缝朝平台起点；孔形/夹紧与层向需样片',thin={'outer_race_lip':1})
for index,(x,y) in enumerate(bolt_xy):
 spacer=ring(f'BEARING_STACK_SPACER_{index+1}',8.2,3.4,10.6,(x,y,59.5))
 part(spacer,'轴承层间支柱 '+str(index+1),'B2',support='通孔轴竖直；通常无支撑，须预览')
# Hollow shaft with full race engagement, shoulder and local D-flats, not a solid proxy.
ss=S['shaft'];shaft=ring('HOLLOW_LOAD_SHAFT',ss['od'],ss['id'],ss['z_max']-ss['z_min'],(0,0,(ss['z_min']+ss['z_max'])/2))
shoulder=ring('SHAFT_INNER_RACE_SHOULDER',34.5,22,1.4,(0,0,73.7),helper=True);unite(shaft,shoulder)
for name,x,zrange in [('DRIVE',14.2,[54.6,64.4]),('NECK',14,[75.4,93])]:boolop(shaft,box('SHAFT_'+name+'_D',(30,80,zrange[1]-zrange[0]),(x+15,0,sum(zrange)/2)))
part(shaft,'空心承力轴（轴肩＋两段D面）','B2',support='轴竖直起点；必须扭转/轴肩样片验证',motion=True)
# Lower split collar with proper clamping ears and through-screw. .2mm provisional axial slack.
collar=ring('SHAFT_LOWER_LOCK_COLLAR',38,30.15,5.6,(0,0,43))
for x in (-4.5,4.5):unite(collar,box('COLLAR_EAR_'+str(x),(6,11,11.4),(x,-17.5,38.3)))
boolop(collar,box('COLLAR_SPLIT',(.8,40,10),(0,-30,43)));hole(collar,(0,0,43),30.15,30);hole(collar,(0,-17.5,38.3),3.4,30,'X');hexhole(collar,(6.5,-17.5,38.3),5.7,2.6,'X')
part(collar,'空心轴下止推夹环','B2',support='轴向竖直起点；耳部孔/开缝须预览',motion=True,thin={'bearing_axial_slack_mm':.2})
# Preserve native ring socket and create shoulder relief. D flat begins above shoulder.
hole(neck,(0,0,74.15),35.0,2.9)
# Moving stop lug and fixed radial ribs: soft45/hard target48, NOT firmware validation.
unite(neck,box('MOVING_YAW_LUG',(8,4,3),(26,0,80.8)))
for sign in (-1,1):
 angle=math.radians(sign*S['hard_stop']['fixed_center_deg']);o=box('FIXED_YAW_STOP_'+str(sign),(10,4,5.5),(28*math.cos(angle),28*math.sin(angle),80.45));o.rotation_euler.z=angle;unite(lid,o)
# Candidate 64T rounded-groove wheels. Native radial Array cutter, retained not baked source.
for driven,cx in ((True,0),(False,-50)):
 label='DRIVEN' if driven else 'DRIVER';wheel=cylinder(label+'_64T_WHEEL',S['pulley']['outer_diameter'],8.4,(cx,0,59.5),helper=False)
 for z in (55.9,63.1):unite(wheel,cylinder(label+'_FLANGE_'+str(z),43.2,1.2,(cx,0,z)))
 # Cutter geometry offset from origin at wheel center, so Empty rotation makes64 true radial teeth.
 g=cylinder(label+'_GROOVE_SOURCE',1.5,6,(cx+20.13,0,59.5));g.data.transform(Matrix.Translation((20.13*U,0,0)));g.location.x=cx*U
 e=bpy.data.objects.new('N5_'+label+'_RADIAL_ARRAY_CONTROL',None);CTRL.objects.link(e);e.location=(cx*U,0,59.5*U);e.rotation_euler.z=2*math.pi/64;e.hide_render=True
 a=g.modifiers.new('64 radial tooth valleys candidate','ARRAY');a.count=64;a.use_relative_offset=False;a.use_constant_offset=False;a.use_object_offset=True;a.offset_object=e;boolop(wheel,g)
 if driven:
  bore=cylinder('DRIVEN_D_BORE',30.15,14,(cx,0,59.5));boolop(bore,box('DRIVEN_D_BORE_FLAT',(20,60,20),(24.4,0,59.5)));boolop(wheel,bore)
  hole(wheel,(19,0,59.5),3.2,18,'X');hexhole(wheel,(18.7,0,59.5),5.7,2.5,'X')
 else:
  hole(wheel,(cx,0,59.5),10,20)
  hole(wheel,(cx,0,55.65),20.4,2.4)
  for x in (-8,8):boolop(wheel,box('HORN_RADIAL_SLOT_'+str(x),(7,2.4,20),(cx+x,0,59.5),bevel=1.1))
 wheel['tooth_profile_status']=S['pulley']['profile_status']
 part(wheel,('从动' if driven else '舵机主动')+'64齿候选带轮','B2',support='轮轴竖直；齿槽/舵盘口袋须样片验带',motion=driven,thin={'flange':1.2})
# Adjustable servo body cradle; no invented spline or ear-hole pattern.
servo=box('SERVO_ADJUSTABLE_CRADLE',(28,34,3.2),(-50,0,9.6),False,bevel=.5)
for dx in (-13,13):unite(servo,box('SERVO_SIDE_'+str(dx),(3.2,20,40.0),(-50+dx,0,31.0)))
for y in (-13,13):
 unite(servo,box('SERVO_EAR_RAIL_'+str(y),(28,7,3.2),(-50,y,50.8)))
 boolop(servo,box('SERVO_EAR_SLOT_'+str(y),(18,3.4,10),(-50,y,50.8),bevel=1.6))
for y in (-12,12):hole(servo,(-50,y,10),3.4,20);base_boss(-50,y,8)
part(servo,'舵机可调耳槽架','B2',support='脚面朝下；耳台悬挑局部支撑；耳孔及输出轴偏移未测')
# Front circular face attachments; radial ribs clipped to original outer control preserve silhouette.
outer=bpy.data.objects['N5_HEAD_RECEIVER_OUTER_CONTROL']
def head_mount(x,z,y=-56.9,d=8,length=9.2):
 o=cylinder(f'HEAD_MOUNT_{x}_{z}',d,length,(x,y,z),'Y');r=math.hypot(x,z-150);a=math.atan2(z-150,x)
 rib=box(f'HEAD_RADIAL_RIB_{x}_{z}',(22,length,8.4),((r+8)*math.cos(a),y,150+(r+8)*math.sin(a)));rib.rotation_euler.y=-a;unite(o,rib);boolop(o,outer,'INTERSECT');unite(head,o);hole(head,(x,y,z),2.8,length+12,'Y');hexhole(head,(x,y+length/2-1.2,z),5.0,2.4,'Y');return o
for deg in S['face_fasteners']['angles_deg']:
 a=math.radians(deg);x=49*math.cos(a);z=150+49*math.sin(a);head_mount(x,z);hole(face,(x,-62.8,z),2.8,15,'Y')
# Privacy slide assembled from base/blade/front retainer; rear-face nut pockets on printed panel.
for x in S['privacy']['screw_x']:
 unite(face,cylinder('FACE_PRIVACY_BOSS_'+str(x),6,3.2,(x,-60.2,189),'Y'));hole(face,(x,-61,189),2.8,20,'Y');hexhole(face,(x,-59.1,189),5,2.2,'Y')
guide=box('PRIVACY_GUIDE_BASE',(38,3.2,13),(6.75,-65.6,189),False,bevel=.5)
boolop(guide,box('GUIDE_OPEN_FRONT_POCKET',(30,3.4,10.6),(6.75,-66.8,189)))
boolop(guide,box('GUIDE_CAMERA_WINDOW',(28,12,8.6),(6.75,-66,189),bevel=.3))
for x in S['privacy']['screw_x']:hole(guide,(x,-65,189),2.8,12,'Y')
part(guide,'隐私滑盖后导向座','B1',(90,0,0),'面向平台；导槽向上；不得与滑片融合',motion=True)
blade=box('PRIVACY_MOVING_BLADE',(16,1.6,10),(0,-66.1,189),False,bevel=.4)
unite(blade,box('PRIVACY_FINGER_TAB',(3,3.2,3),(0,-68.4,189),bevel=.6))
part(blade,'隐私滑片（13.5mm行程）','B1',(90,0,0),'平放；拨片悬挑局部支撑',motion=True,thin={'blade':1.6})
cap=box('PRIVACY_FRONT_RETAINER',(38,1.2,13),(6.75,-67.8,189),False,bevel=.4);boolop(cap,box('RETAINER_SLIDE_WINDOW',(28,12,8.6),(6.75,-67,189),bevel=.3))
for x in S['privacy']['screw_x']:hole(cap,(x,-67.8,189),2.8,12,'Y')
part(cap,'隐私导向前压框','B1',(90,0,0),'平面朝平台；单独件，先装滑片再封框',motion=True,thin={'retainer':1.2})
# PCB-independent LCD frame and pressure frame; perimeter clamp rather than imaginary PCB holes.
lcd=box('LCD_BUDGET_FRAME',(89,3.8,59),(0,-55.8,145),False,bevel=3)
boolop(lcd,box('LCD_FRAME_WINDOW',(79,12,49),(0,-55.8,145),bevel=2))
for x in (-47.3,47.3):
 unite(lcd,box('LCD_FRAME_EAR_'+str(x),(8,3.8,10),(x,-55.8,145),bevel=1));hole(lcd,(x,-55.8,145),2.8,20,'Y');head_mount(x,145,-49.4,8,9.0)
part(lcd,'LCD后支承框（预算边缘夹持）','B3',(90,0,0),'框面平放；不使用假定PCB孔位',motion=True)
lcdclamp=box('LCD_PRESSURE_FRAME',(89,1.6,59),(0,-60.6,145),False,bevel=3);boolop(lcdclamp,box('LCD_PRESSURE_WINDOW',(79,10,51),(0,-60.6,145),bevel=2))
for x in (-47.3,47.3):unite(lcdclamp,box('LCD_PRESSURE_EAR_'+str(x),(8,1.6,10),(x,-60.6,145),bevel=1));hole(lcdclamp,(x,-60.6,145),2.8,20,'Y')
# Frame holes are outside85mm budget; verify populated PCB and clamp spacing before tightening.
part(lcdclamp,'LCD前压框（间距待实测）','B3',(90,0,0),'框面平放；仅夹预算边缘，实测玻璃/元件高度',motion=True,thin={'front_pressure_frame':1.6})
cam=box('CAMERA_CRADLE',(25.4,14.8,23.4),(0,-53.8,188),False,bevel=1)
boolop(cam,box('CAMERA_BUDGET_POCKET',(20.6,16,18.6),(0,-50.8,188),bevel=.3));hole(cam,(0,-54,189),8.8,30,'Y')
for x in (-23,23):
 unite(cam,box('CAMERA_EAR_'+str(x),(14,4.6,8),(18 if x>0 else -18,-58.9,188),bevel=.6));hole(cam,(x,-58.9,188),2.8,20,'Y');head_mount(x,188,-52,8,9.2)
part(cam,'摄像模组预算托架','B3',(90,0,0),'镜头孔轴竖直；FPC出口/镜头凸高未测',motion=True)
camcap=box('CAMERA_BACK_RETAINER',(26,2.4,24),(0,-45.2,188),False,bevel=1);boolop(camcap,box('CAMERA_FPC_EXIT',(17,10,15),(0,-45.2,190),bevel=.5))
# Side screw reception belongs to this cradle, not to camera PCB.
for x in (-10.8,10.8):
 unite(cam,cylinder('CAMERA_CAP_RECEIVER_'+str(x),5.6,4.2,(x,-48.5,174.8),'Y'));hole(cam,(x,-47.5,174.8),2.8,15,'Y')
 unite(camcap,cylinder('CAMERA_CAP_EAR_'+str(x),5.6,2.4,(x,-45.2,174.8),'Y'));hole(camcap,(x,-45.2,174.8),2.8,12,'Y')
part(camcap,'摄像托架后压片＋排线口','B3',(90,0,0),'平面朝平台；不夹排线，不假定模组孔位',motion=True)
# Neck/head existing M3 holes get true captive-nut access.
for x in (-26,26):hexhole(neck,(x,0,98),5.7,2.6)
# Base cover receivers: tongues bridge inner lid height; cup bosses tie into cup wall.
for x in (-58,58):
 for y in (-52,52):
  b=cylinder(f'COVER_CUP_BOSS_{x}_{y}',12,10.5,(x,y,60.75));unite(cup,b)
  # Radial bridge to shell, so bosses are not disconnected islands.
  angle=math.atan2(y/(164/180),x);rib=box(f'COVER_CUP_RIB_{x}_{y}',(13,8,10.5),(x+4*math.cos(angle),y+4*math.sin(angle),60.75));rib.rotation_euler.z=angle;unite(cup,rib)
  hole(cup,(x,y,60),3.4,22);hexhole(cup,(x,y,57.5),5.7,2.6)
  # Nut inserted from interior-side underside of receiver before electronics installation.
  unite(lid,cylinder(f'COVER_LID_RECEIVER_{x}_{y}',8,6,(x,y,69)));hole(lid,(x,y,69),3.4,28)
# Native outer cap clips screw receiver additions flush with accepted shoulder silhouette.
lv=[v.co.copy() for v in lid.data.vertices];iend=next(i for i,v in enumerate(lv) if i>3 and abs(v.x)<1e-8 and abs(v.z/U-78)<.02)
lcoords=[Vector((0,0,65.8*U)),Vector((lv[0].x,0,65.8*U))]+lv[:iend+1]
lme=bpy.data.meshes.new('N5_LID_OUTER_SECTION');lme.from_pydata(lcoords,[(i,(i+1)%len(lcoords)) for i in range(len(lcoords)) if not (abs(lcoords[i].x)<1e-9 and abs(lcoords[(i+1)%len(lcoords)].x)<1e-9)],[])
lclip=bpy.data.objects.new('N5_LID_OUTER_CLIP',lme);CTRL.objects.link(lclip);lclip.scale=lid.scale.copy();lclip.hide_render=True;lm=lclip.modifiers.new('Native flush receiver clip','SCREW');lm.axis='Z';lm.steps=128;lm.render_steps=128;lm.use_merge_vertices=True;lm.merge_threshold=1e-6;lm.use_normal_calculate=True
for lm in lid.modifiers:
 if lm.type=='BOOLEAN' and lm.operation=='UNION' and 'COVER_LID_RECEIVER_' in lm.object.name:boolop(lm.object,lclip,'INTERSECT')
# STOP cap and independent tactile holder: travel/height parameter budget, no mechanical lever to BOOT.
key=box('STOP_KEY_CAP',(12.2,8.2,2),(0,-49,77.5),False,bevel=2)
unite(key,box('STOP_KEY_STEM',(4,4,4.6),(0,-49,74.5),bevel=.4));unite(key,box('STOP_KEY_RETENTION_FOOT',(14.2,10.2,1.2),(0,-49,74.8),bevel=.5))
part(key,'前肩停止键帽＋短键柱','B1',support='键面朝平台起点；行程/导向须样片',thin={'cap':2.0,'retention_foot':1.2})
keyholder=box('TACTILE_SWITCH_HOLDER',(40,15,3.2),(0,-49,65.6),False,bevel=.6)
boolop(keyholder,box('SWITCH_6MM_BUDGET',(6.4,6.4,4),(0,-49,67.4),bevel=.3))
for x in (-15,15):
 unite(keyholder,box('KEY_GUIDE_PILLAR_'+str(x),(3,12,7.8),(9.5 if x>0 else -9.5,-49,70.7)))
 unite(keyholder,cylinder('KEY_CLAMP_STANDOFF_'+str(x),8,4,(x,-49,68.9)));unite(lid,cylinder('KEY_HOLDER_RECEIVER_'+str(x),8,5,(x,-49,73.4)));hole(lid,(x,-49,71),2.8,20);hole(keyholder,(x,-49,70),2.8,20)
part(keyholder,'外接轻触键托座及限行程导向','B1',support='底面朝下；开口朝上；6mm开关预算，非BOOT连杆')
# Electronics: open-topped edge cradles, removable retainers; no fictitious board mounting holes.
board=box('MAINBOARD_EDGE_CRADLE',(70,6,32),(0,54.5,47.5),False,bevel=.6)
boolop(board,box('MAINBOARD_INSERTION_SLOT',(63.2,2.4,40),(0,54,52)))
boolop(board,box('MAINBOARD_COMPONENT_WINDOW',(58,16,24),(0,54.5,49)))
for x in (-33.4,33.4):
 unite(board,box('MAINBOARD_VERTICAL_LEG_'+str(x),(4,6,31),(x,54.5,23.5)))
 unite(board,box('MAINBOARD_FOOT_'+str(x),(9,14,3.2),(x,51.5,9.6),bevel=.5));hole(board,(x,49,9),3.4,20);base_boss(x,49,8)
part(board,'核心板开放边缘托架','B3',(0,0,0),'脚面朝下；槽/跨桥局部支撑，排针口待测')
bret=box('MAINBOARD_TOP_RETAINER',(70,2.4,5),(0,50.1,62.5),False,bevel=.5)
unite(bret,box('MAINBOARD_TOP_CAPTURE_LIP',(64,6.4,2.4),(0,53,64.9)))
for x in (-33.4,33.4):hole(bret,(x,50.1,62.5),2.8,18,'Y');hole(board,(x,54.5,62.5),2.8,18,'Y')
part(bret,'核心板可拆上压条','B3',(90,0,0),'压条面平放；只夹板边，不遮连接器')
for index,x in enumerate((-16.3,16.3),1):
 m=box(f'FIXED_MIC_DUCT_CRADLE_{index}',(22,10,16),(x,70,52),False,bevel=1.2)
 boolop(m,box('MIC_INSERT_POCKET_'+str(index),(16.6,9,12.6),(x,68.5,52),bevel=.2))
 unite(m,box('MIC_STAND_'+str(index),(8,4,34),(x,69,25)))
 unite(m,box('MIC_REAR_STEP_'+str(index),(8,8.2,4),(x,71.1,40)));unite(m,box('MIC_REAR_UPPER_'+str(index),(8,2.4,9),(x,74,43.5)));unite(m,box('MIC_FOOT_'+str(index),(16,12,3.2),(x,65,9.6),bevel=.6));hole(m,(x,65,10),3.4,20);base_boss(x,65,8)
 duct=ring('MIC_ACOUSTIC_DUCT_'+str(index),7.2,2.8,4.3,(x,75.15,52),'Y',True);unite(m,duct);hole(m,(x,75,52),2.8,18,'Y')
 part(m,'固定麦托架＋硬声管 '+str(index),'B3',support='脚面朝下；声管内孔局部支撑，端口及贴壳位置未测')
 ret=box('MIC_RETAINER_'+str(index),(31.6,2.4,8),(x,63.6,57.8),False,bevel=.4)
 for dx in (-12,12):unite(m,cylinder('MIC_CLAMP_RECEIVER_'+str(index)+str(dx),8,4,(x+dx,67,57.8),'Y'));hole(ret,(x+dx,63.6,57.8),2.8,15,'Y');hole(m,(x+dx,70,57.8),2.8,18,'Y')
 part(ret,'固定麦前压条 '+str(index),'B3',(90,0,0),'面平放；不要堵拾音口')
for cid,cn in [('I2S_AMP','功放开放托盘'),('BATTERY_CHARGER','充电保护板开放托盘')]:
 original=next(c for c in P['components'] if c['id']==cid);override=S['provisional_relocations'].get(cid,{});c={**original,**override};x,y,z=c['center'];w,d,h=c['body'];floor=z-h/2-2.6;ow=w+5.4;od=d+5.4
 tray=box(cid+'_OPEN_TRAY',(ow,od,8),(x,y,floor+4),False,bevel=.8);boolop(tray,box(cid+'_BOARD_SLOT',(w+.6,d+.6,10),(x,y,floor+7.4),bevel=.3))
 for dx in (-ow/2+2,ow/2-2):
  unite(tray,box(cid+'_LEG_'+str(dx),(4,od,floor-6.8),(x+dx,y,(floor+7)/2)))
 unite(tray,box(cid+'_FOOT',(ow,od,3.2),(x,y,8.6),bevel=.5));hole(tray,(x,y,8.5),3.4,16);base_boss(x,y,7)
 boolop(tray,box(cid+'_WIRE_EXIT',(w-3,7,9),(x,y-od/2,floor+7)))
 part(tray,cn,'B3',support='底面朝下；连线口朝上；预算边缘夹持，焊点/端口未测')
# Battery remains optional reserve; unvalidated portable power, not a working charging system.
bat=box('OPTIONAL_BATTERY_TRAY',(36,61,12),(53,0,11.6),False,bevel=1);boolop(bat,box('BATTERY_CLEARANCE',(30.6,55.6,14),(53,0,15.5),bevel=.6))
for y in (-32,32):unite(bat,box('BATTERY_FIX_EAR_'+str(y),(10,10,2.4),(53,y,6.8),bevel=.6));hole(bat,(53,y,7),3.4,15);base_boss(53,y,5.6)
boolop(bat,box('BATTERY_CABLE_EXIT',(12,10,10),(53,-31,16)))
part(bat,'选装电池开放托盘（90度避让）','B3',support='底面朝下；不得压电芯；电源路径仍未放行')
# Speaker cradle and separate retaining ring; bought speaker is never exported.
sp=ring('SPEAKER_AXIAL_CRADLE',46,40.5,22,(0,-57,33),'Y')
unite(sp,ring('SPEAKER_REAR_OUTER_RACE_LIP',46,37,1.4,(0,-46.7,33),'Y',True))
for x in (-23,23):
 unite(sp,box('SPEAKER_EAR_'+str(x),(8,22,8),(x,-57,33),bevel=.6));hole(sp,(x,-57,33),3.4,36,'Y')
unite(sp,box('SPEAKER_FOOT',(54,22,3.2),(0,-57,9.6),bevel=.6))
for x in (-23,23):unite(sp,box('SPEAKER_LEG_'+str(x),(6,16,25.4),(x,-57,23.7)));hole(sp,(x,-57,10),3.4,20);base_boss(x,-57,8)
part(sp,'扬声器圆筒托架＋后挡肩','B3',(90,0,0),'扬声器孔轴竖直起点；脚部支撑待预览')
sret=ring('SPEAKER_FRONT_RETAINER',46,36,2.4,(0,-69.5,33),'Y')
for x in (-23,23):unite(sret,box('SPEAKER_RET_BRIDGE_'+str(x),(8,2.4,8),(x*.91,-69.5,33)));unite(sret,cylinder('SPEAKER_RET_EAR_'+str(x),8,2.4,(x,-69.5,33),'Y'));hole(sret,(x,-69.5,33),3.4,10,'Y')
part(sret,'扬声器前压圈','B3',(90,0,0),'压圈平放，胶垫/实际外径未测')
# Cup-integrated front sound guide ties into shell, deliberately not another loose proxy.
sound=ring('CUP_SOUND_GUIDE',46,40.5,7.6,(0,-74.7,33),'Y',True)
# Restrict to original cup exterior: create native Screw closed outer solid using cup source outer radial chain.
verts=[v.co.copy() for v in cup.data.vertices];outer_end=next(i for i,v in enumerate(verts) if i>5 and abs(v.z/U-66)<.01)
coords=verts[:outer_end+1]+[Vector((0,0,66*U))];me=bpy.data.meshes.new('N5_CUP_OUTER_PROFILE');me.from_pydata(coords,[(i,(i+1)%len(coords)) for i in range(len(coords)) if not (abs(coords[i].x)<1e-9 and abs(coords[(i+1)%len(coords)].x)<1e-9)],[]);solid=bpy.data.objects.new('N5_CUP_OUTER_CLIP',me);CTRL.objects.link(solid);solid.scale=cup.scale.copy();mod=solid.modifiers.new('Native outer clipping envelope','SCREW');mod.axis='Z';mod.steps=128;mod.render_steps=128;mod.use_merge_vertices=True;mod.merge_threshold=1e-6;mod.use_normal_calculate=True;solid.hide_render=True
boolop(sound,solid,'INTERSECT');unite(cup,sound)
# Ensure shoulder cup bosses never protrude original surface.
for mod in cup.modifiers:
 if mod.type=='BOOLEAN' and mod.operation=='UNION' and ('COVER_CUP_' in mod.object.name):boolop(mod.object,solid,'INTERSECT')
# Cable saddles: two separately manufactured pieces with real seats and single fixing screw.
for index,center in enumerate(((16,34,13),(36,0,102.5)),1):
 x,y,z=center;clip=box('CABLE_SADDLE_'+str(index),(16,14,6),(x,y,z),False,bevel=.8)
 boolop(clip,box('CABLE_OPEN_SLOT_'+str(index),(11,18,4.3),(x,y,z+1.3),bevel=.5));hole(clip,(x,y,z-1.8),3.4,16)
 part(clip,'线束固定鞍 '+str(index),'B3',support='平底朝下；槽向上；束带绕槽，禁止扎紧FPC',motion=index==2)
 if index==1:base_boss(x,y,10)
 else:
  # Above flange below cable reserve105; fixing boss belongs to head floor, not cable keepout.
  unite(head,cylinder('HEAD_CABLE_SADDLE_RECEIVER',9,4.5,(x,y,97.25)));hole(head,(x,y,97),3.4,18);hexhole(head,(x,y,93.4),5.7,2.6)
# Update two relocated hardware and keep-out copies only (never mutate v4).
for cid,c in S['provisional_relocations'].items():
 for name in (cid,'KEEP_OUT_'+cid):
  o=bpy.data.objects.get('N5_'+name)
  if not o:continue
  o.location=Vector(c['center'])*U
  if cid=='BATTERY':o.rotation_euler.z=math.pi/2
for km in bpy.data.objects['N5_STOP_BUTTON_OPENING'].modifiers:
 if km.type=='BEVEL':km.width=1.0*U
boolop(neck,ring('NECK_BOSS_UNDERSIDE_RELIEF',80,46,.8,(0,0,94.8),helper=True))
boolop(lcd,cylinder('LCD_ROUND_MOUTH_CLIP',106,20,(0,-55.8,150),'Y'),'INTERSECT');boolop(lcdclamp,cylinder('LCD_FRONT_ROUND_MOUTH_CLIP',105.8,12,(0,-60.6,150),'Y'),'INTERSECT')
# Explicit nominal mating clearances; not fitted or hardware-validated interfaces.
hole(head,(0,0,97.45),62.4,4.5)
boolop(neck,box('NECK_UPPER_SEAT_RETREAT',(160,160,150),(0,0,-.4)))
for x in S['privacy']['screw_x']:hole(cam,(x,-60.2,189),6.4,3.6,'Y')
bpy.data.objects['N5_DISPLAY_CAMERA_SHARED_ACTIVITY_RESERVE'].location=Vector((0,20,118.5))*U
# All newly-created head controls must follow head yaw exactly; natives remain editable.
head_owners={head,face,neck}|{p['object_ref'] for p in parts if p['object_ref'].parent==yaw}
visited=set()
def move_controls(o):
 for m in o.modifiers:
  for prop in ('object','offset_object'):
   t=getattr(m,prop,None)
   if t and t not in visited:
    visited.add(t)
    if t.name.startswith('N5_') and t.name in CTRL.objects:attach_yaw(t);move_controls(t)
for o in head_owners:move_controls(o)
yaw.rotation_euler.z=0;bpy.context.view_layer.update()
boolop(head,bpy.data.objects['N5_HEAD_BOTTOM_TRIM'])
# Re-open original grille after adding the interior sound guide.
boolop(cup,bpy.data.objects['N5_SPEAKER_SLOT_SOURCE'])
# Source .blend saved intact before evaluated cleanup/export. Failed export never becomes release.
blend=ROOT/'EffMeet2_NOMI_布局A_v5_拆件候选.blend';scene.camera=bpy.data.objects['N5_CAM_HERO'];bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
# Evaluated export mesh QA. The cleanup lives ONLY in export copies; native source is not applied.
def stats(bm):
 bm.verts.ensure_lookup_table();adj={v.index:set() for v in bm.verts}
 for e in bm.edges:
  a,b=[v.index for v in e.verts];adj[a].add(b);adj[b].add(a)
 remaining=set(adj);count=0
 while remaining:
  count+=1;todo=[remaining.pop()]
  while todo:
   for k in adj[todo.pop()]&remaining:remaining.remove(k);todo.append(k)
 points=[v.co for v in bm.verts];bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
 return {'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'wire_edges':sum(e.is_wire for e in bm.edges),'loose_vertices':sum(not v.link_edges for v in bm.verts),'zero_area_faces':sum(f.calc_area()==0 for f in bm.faces),'micro_faces_below_1e8_mm2':sum(0<f.calc_area()<1e-8 for f in bm.faces),'short_edges_below_0001_mm':sum(e.calc_length()<.001 for e in bm.edges),'components':count,'volume_mm3':abs(bm.calc_volume(signed=True)),'minimum_area_mm2':min(f.calc_area() for f in bm.faces),'bounds_mm':bounds}
def cleaned(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me);bm.transform(e.matrix_world);bm.transform(Matrix.Scale(1/U,4));e.to_mesh_clear();raw=stats(bm)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
 loose=[v for v in bm.verts if not v.link_edges]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
 bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.normal_update();wire=[e for e in bm.edges if e.is_wire];
 if wire:bmesh.ops.delete(bm,geom=wire,context='EDGES')
 loose=[v for v in bm.verts if not v.link_edges]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 return bm,raw

def binary_stl(path,bm,header):
 tris=list(bm.faces)
 with path.open('wb') as f:
  f.write(header.encode('ascii')[:80].ljust(80,b' '));f.write(struct.pack('<I',len(tris)))
  for face in tris:
   assert len(face.verts)==3
   f.write(struct.pack('<12fH',*face.normal,*[v for vert in face.verts for v in vert.co],0))
validation=[];export_geometry={};validator=load('validator',SK/'blender-geometry-validation/scripts/validate_scene.py');independent=[]
for row in parts:
 o=row['object_ref'];bm,raw=cleaned(o);clean=stats(bm);blocking=[k for k in ('boundary_edges','nonmanifold_edges','wire_edges','loose_vertices','zero_area_faces','micro_faces_below_1e8_mm2') if clean[k]]
 if clean['components']!=1:blocking.append('components')
 changes=max(abs(clean['bounds_mm'][s][i]-raw['bounds_mm'][s][i]) for s in (0,1) for i in range(3));volchange=abs(clean['volume_mm3']-raw['volume_mm3'])/max(raw['volume_mm3'],1)
 if changes>.01 or volchange>.001:blocking.append('cleanup_shape_delta')
 # Independently audit a disposable metre-scale evaluated mesh with no modifiers.
 me=bpy.data.meshes.new('QA_'+row['id']);bm.to_mesh(me);me.transform(Matrix.Scale(U,4));qa=bpy.data.objects.new('QA_'+row['id'],me);C.objects.link(qa);bpy.context.view_layer.update();metrics,issues=validator._mesh_metrics(qa,False);independent.append({'id':row['id'],'issues':issues,'metrics':metrics});bpy.data.objects.remove(qa,do_unlink=True);bpy.data.meshes.remove(me)
 # Independent warnings retained, not overwritten to PASS. No release flag changes.
 row['mesh_status']='BLOCKED' if blocking else 'GEOMETRY_ONLY_PASS';row['slicer_status']='NOT_RUN';row['sample_print_status']='NOT_RUN';row['release_status']='CANDIDATE_NOT_RELEASED';row['bounds_mm']=clean['bounds_mm'];row['size_mm']=[clean['bounds_mm'][1][i]-clean['bounds_mm'][0][i] for i in range(3)]
 report={'id':row['id'],'object':o.name,'raw':raw,'cleaned':clean,'cleanup_max_bound_change_mm':changes,'cleanup_relative_volume_change':volchange,'blocking':blocking,'independent_issues':issues};validation.append(report)
 print('QA',row['id'],row['mesh_status'],blocking,flush=True)
 if not blocking:
  # Orientation is a START hypothesis. STL is on bed in mm; assembly pose is retained in .blend.
  bmcopy=bm.copy();R=Matrix.Identity(4)
  for axis,deg in zip('XYZ',row['orientation_euler_deg']):R=Matrix.Rotation(math.radians(deg),4,axis)@R
  bmcopy.transform(R);mins=[min(v.co[i] for v in bmcopy.verts) for i in range(3)];bmcopy.transform(Matrix.Translation(Vector([-v for v in mins])));bmcopy.normal_update()
  filename=row['id']+'_'+o.name.removeprefix('N5_')+'_UNVERIFIED.stl';binary_stl(OUT/filename,bmcopy,'EFFMEET2 V5 CANDIDATE NOT RELEASED MM')
  row['stl']='candidate-stl/'+filename;row['print_size_mm']=[max(v.co[i] for v in bmcopy.verts) for i in range(3)];row['stl_sha256']=hashlib.sha256((OUT/filename).read_bytes()).hexdigest();export_geometry[row['id']]={'v':[[float(c) for c in v.co] for v in bmcopy.verts],'f':[[v.index for v in f.verts] for f in bmcopy.faces]};bmcopy.free()
 bm.free()
(PROD/'mesh-audit.json').write_text(json.dumps({'scope':'evaluated candidates, NOT manufacturing release','cleanup_weld_mm':.00001,'parts':validation,'all_closed':all(not r['blocking'] for r in validation),'hardware_validated':False,'manufacturing_ready':False},indent=2),encoding='utf8')
(PROD/'independent-mesh-audit.json').write_text(json.dumps({'scope':'official skill mesh validator on cleaned disposable export meshes','status':'FAIL' if any(r['issues'] for r in independent) else 'PASS','parts':independent},indent=2),encoding='utf8')
# Preserve original object state; cloning/new meshes never alters protected originals.
after=snap.capture_snapshot(protected);unchanged=before['objects']==after['objects']
(PROD/'protected-scene-before.json').write_text(json.dumps(before,indent=2),encoding='utf8');(PROD/'protected-scene-after.json').write_text(json.dumps(after,indent=2),encoding='utf8');
(PROD/'protected-scene-check.json').write_text(json.dumps({'protected_objects':len(protected),'unchanged':unchanged,'earlier_scenes':sorted(s.name for s in bpy.data.scenes if s!=scene),'scope':'original object/data/modifier snapshot equality'},indent=2),encoding='utf8');assert unchanged
rows=[{k:v for k,v in r.items() if k!='object_ref'} for r in parts]
(ROOT/'parts.json').write_text(json.dumps({'revision':'v5','status':'conditional_candidate','units':'mm','stage':'reversible_blockout','manufacturing_ready':False,'hardware_validated':False,'plates_frozen':False,'parts':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
# Graph separates topology closure from hardware validity and semantic part approval.
graph={'schema_version':'1.0','part_graph_status':'approved','approval_scope':'User explicitly authorized this manufactured-part segmentation, NOT final geometry/hardware release','parts':[],'relationships':[]}
for r in rows:
 o=bpy.data.objects[r['object']];mods=[m.type for m in o.modifiers]
 graph['parts'].append({'id':r['id'],'role':'primary_form' if r['id'] in ('P01','P02','P04','P05') else 'structural_part','form_level':'primary' if r['id'] in ('P01','P02','P04','P05') else 'structural','physical_function':r['function'],'separation_policy':'separate_manufactured_part','separation_reason':'independent assembly, motion, service or measured fit interface','construction_method':'native profile/Boolean fusion with evaluated export cleanup','connection_method':'mechanical assembly, unverified budget interface','combination_level':'C_PHYSICAL_ASSEMBLY','final_object_name':r['object'],'blockout_object_names':[r['object']],'blockout_proxy':False,'topology_status':'deferred','topology_evidence':{'report':'mesh-audit.json','connected_component_count':next(v['cleaned']['components'] for v in validation if v['id']==r['id'])},'native_system':mods,'assembly_interfaces':[{'status':'unverified','policy':'parameterized budget interface; do not claim real fit'}],'requirements':{'single_component':True},'material':r['material']+' '+r['color'],'export_owner':r['id'],'clearance_policy':'sample pending'})
(PROD/'construction_graph.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf8')
(PROD/'export-geometry.json').write_text(json.dumps(export_geometry,separators=(',',':')),encoding='utf8')
# Positional yaw sanity; stage enum and all release booleans remain unchanged.
yaw_report=[]
for deg in (-45,0,45):
 yaw.rotation_euler.z=math.radians(deg);bpy.context.view_layer.update();e=head.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();zs=[(e.matrix_world@v.co).z/U for v in me.vertices];bm=bmesh.new();bm.from_mesh(me);bm.transform(e.matrix_world);yaw_report.append({'angle_deg':deg,'head_min_z_mm':min(zs),'gap_from_original_lid_crown_mm':min(zs)-78,'volume_mm3':abs(bm.calc_volume())/U**3,'boundary_edges':sum(x.is_boundary for x in bm.edges),'nonmanifold_edges':sum(not x.is_manifold for x in bm.edges),'dynamic_cable_test':'NOT_RUN'});bm.free();e.to_mesh_clear()
yaw.rotation_euler.z=0;bpy.context.view_layer.update();(PROD/'yaw-audit.json').write_text(json.dumps({'poses':yaw_report,'firmware_tested':False,'scope':'native dependencies and head bounds; no flex/hardware test'},indent=2),encoding='utf8')
# Save final source assembled; presentation copies/proxies are never in export table.
for o in scene.objects:
 if 'COMPONENT_PROXIES' in str([c.name for c in o.users_collection]):o.hide_render=o.name not in ('N5_LCD_GLASS_PROXY','N5_CAMERA_LENS_PROXY','N5_PURCHASED_SILICONE_FOOT')
scene.camera=bpy.data.objects['N5_CAM_HERO'];bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
(PROD/'source-binding.json').write_text(json.dumps({'parameters_sha256':hashlib.sha256(PARAM.read_bytes()).hexdigest(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'input_v4_sha256':hashlib.sha256((REV/'EffMeet2_NOMI_布局A_工程候选_v4.blend').read_bytes()).hexdigest(),'status':'candidate_not_released'},indent=2),encoding='utf8')
# Keep rendered evidence small and relevant. Every image uses real native candidate geometry.
if os.environ.get('EFFMEET_SKIP_RENDER')!='1':
 def render(filename,cam):
  scene.camera=bpy.data.objects['N5_CAM_'+cam];scene.render.filepath=str(REN/filename);bpy.ops.render.render(write_still=True)
 render('01_hero_candidate.png','HERO');render('02_front_candidate.png','FRONT');render('03_side_candidate.png','SIDE');render('04_top_candidate.png','TOP')
 for o in (cup,lid,head,face):o.hide_render=True
 for o in scene.objects:
  if 'COMPONENT_PROXIES' in str([c.name for c in o.users_collection]):o.hide_render=False
 render('05_internal_candidate.png','INTERNAL')
 for o in (cup,lid,head,face):o.hide_render=False
print('SPLIT_COMPLETE',len(rows),'parts',len(export_geometry),'exports',flush=True)

