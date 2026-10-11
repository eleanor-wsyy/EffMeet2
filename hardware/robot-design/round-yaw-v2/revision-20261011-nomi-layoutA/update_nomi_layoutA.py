"""Reversible NOMI-guided layout A candidate. Never export print parts here.
Load prior blend explicitly. New scene is isolated; earlier objects/worlds stay intact.
Run: blender --background <v2.blend> --python update_nomi_layoutA.py
"""
import bpy,bmesh,math,json,hashlib,os,importlib.util
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT.parent/'parameters.json').read_text(encoding='utf-8'))
OUT=ROOT/'renders'/os.environ.get('EFFMEET_REVIEW','review-01');OUT.mkdir(parents=True,exist_ok=True)
PROD=ROOT/'production';U=.001
if any(OUT.glob('*.png')):raise FileExistsError('Use a fresh EFFMEET_REVIEW to preserve evidence')
# Capture actual Blender state before any scene mutation.
SK=Path.home()/'.codex'/'skills'
spec=importlib.util.spec_from_file_location('snapshot',SK/'blender-geometry-validation/scripts/snapshot_scene.py')
snap=importlib.util.module_from_spec(spec);spec.loader.exec_module(snap)
protected=sorted(o.name for o in bpy.data.objects)
before=snap.capture_snapshot(protected)
(PROD/'protected-scene-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
scene=bpy.data.scenes.new('N4_NOMI_LAYOUT_A_CANDIDATE');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
def col(n):
 c=bpy.data.collections.new('N4_'+n);scene.collection.children.link(c);return c
shellcol=col('SHELLS');cutcol=col('NATIVE_CONTROLS');hwcol=col('COMPONENT_PROXIES');keepcol=col('KEEP_OUTS');presentation=col('REVIEW_ONLY');camcol=col('CAMERAS');supportcol=col('SUPPORT_ENVELOPES')
headparts=[];hardware=[];shells=[];controls=[];supports=[]
def material(n,c,rough=.65,metal=0,emission=0):
 m=bpy.data.materials.new('N4_'+n);m.diffuse_color=(*c,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if n=='PLA_BLACK_PREVIEW':bs.inputs['Base Color'].default_value=(.006,.007,.008,1);bs.inputs['Specular IOR Level'].default_value=.25
 if emission:bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=emission
 return m
GREY=material('PLA_GREY_PREVIEW',(.63,.65,.66),.72);BLACK=material('PLA_BLACK_PREVIEW',(.018,.021,.024),.68)
GLASS=material('LCD_ONLY',(.012,.016,.022),.23);PCB=material('PCB_PROXY',(.06,.25,.20),.62)
METAL=material('BEARING_PROXY',(.40,.43,.47),.3,.65);BLUE=material('SERVO_PROXY',(.15,.31,.44),.55)
BAT=material('BATTERY_PROXY',(.37,.41,.46),.6);EYE=material('WARM_DISPLAY_PREVIEW',(1,.79,.52),.4,emission=1.4)
CORAL=material('STATUS_PREVIEW',(1,.23,.12),.4,emission=1);CABLE=material('FPC_ROUTE_PROXY',(.62,.35,.11),.6)
def move(o,c):
 for a in list(o.users_collection):a.objects.unlink(o)
 c.objects.link(o)
def reg(o,n,m=GREY,c=shellcol):
 o.name='N4_'+n;move(o,c)
 if m and hasattr(o.data,'materials'):o.data.materials.append(m)
 o['stage']='reversible_blockout';o['manufacturing_ready']=False
 if c==shellcol:shells.append(o)
 if c==cutcol:controls.append(o);o.hide_render=True;o.hide_set(True);o.display_type='WIRE'
 if c==hwcol:hardware.append(o);o['actual_product_CAD']=False
 if c==supportcol:supports.append(o);o['interface_status']='provisional envelope, not manufactured support'
 return o
def cube(n,size,center,m=GREY,c=shellcol,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)*U);o=reg(bpy.context.object,n,m,c);o.dimensions=Vector(size)*U
 o.data.transform(Matrix.Diagonal((*o.scale,1)));o.scale=(1,1,1)
 if bevel:
  mod=o.modifiers.new('Scale-aware edge radius','BEVEL');mod.width=bevel*U;mod.segments=5
 return o
def cyl(n,d,h,center,m=GREY,c=shellcol,axis='Z'):
 bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=d/2*U,depth=h*U,location=Vector(center)*U)
 o=reg(bpy.context.object,n,m,c)
 if axis=='Y':o.data.transform(Matrix.Rotation(math.pi/2,4,'X'))
 for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
 return o
def boolean(o,c,op='DIFFERENCE'):
 mod=o.modifiers.new(op+' '+c.name,'BOOLEAN');mod.operation=op;mod.solver='EXACT';mod.object=c
 return mod
def ring(n,od,idd,h,center,m,c,axis='Z'):
 o=cyl(n,od,h,center,m,c,axis);cut=cyl(n+'_BORE',idd,h+4,center,None,cutcol,axis);boolean(o,cut);return o,cut
# Source profiles and native Screw own revolved surfaces. No individually baked radial fragments.
def screw(n,profile,axis='Z',center=(0,0,0),m=GREY,c=shellcol):
 coords=[(r*U,0,z*U) if axis=='Z' else (r*U,z*U,0) for r,z in profile]
 edges=[(i,i+1) for i in range(len(coords)-1)]
 me=bpy.data.meshes.new('N4_'+n+'_PROFILE');me.from_pydata(coords,edges,[]);me.update()
 o=bpy.data.objects.new('N4_'+n,me);c.objects.link(o);o.location=Vector(center)*U;reg(o,n,m,c)
 mod=o.modifiers.new('Editable radial section','SCREW');mod.axis=axis;mod.angle=2*math.pi;mod.steps=128;mod.render_steps=128;mod.use_merge_vertices=True;mod.merge_threshold=1e-6;mod.use_smooth_shade=True;mod.use_normal_calculate=True
 o['native_owner']='SCREW';return o
def arc(cr,cz,r,a,b,n=28):return [(cr+r*math.cos(a+(b-a)*i/n),cz+r*math.sin(a+(b-a)*i/n)) for i in range(n+1)]
# True 2.4mm cup bottom, 0.3mm removable shoulder seam; base size remains180x164x76.
a=math.asin((66-52)/26);ai=math.asin((66-52)/23.6)
cp=[(0,2),(72,2)]+arc(72,20,18,-math.pi/2,0)[1:]+[(90,52)]+arc(64,52,26,0,a)[1:]+arc(64,52,23.6,ai,0)+[(87.6,20)]+arc(72,20,15.6,0,-math.pi/2)[1:]+[(0,4.4)]
cup=screw('BASE_CUP',cp);cup.scale.y=164/180
al=math.asin((66.3-52)/26);ail=math.asin((66.3-52)/23.6)
lp=arc(64,52,26,al,math.pi/2)+[(0,78),(0,75.6),(64,75.6)]+arc(64,52,23.6,math.pi/2,ail)[1:]
# Close around outer/inner seam, but omit the zero-radius pole edge to avoid loose axial geometry.
cp0=cp;cup.data.clear_geometry();cup.data.from_pydata([(r*U,0,z*U) for r,z in cp],[(i,(i+1)%len(cp)) for i in range(len(cp)) if not(cp[i][0]==0 and cp[(i+1)%len(cp)][0]==0)],[])
lid=screw('BASE_LID',lp);lid.scale.y=164/180
lid.data.clear_geometry();lid.data.from_pydata([(r*U,0,z*U) for r,z in lp],[(i,(i+1)%len(lp)) for i in range(len(lp)) if not(lp[i][0]==0 and lp[(i+1)%len(lp)][0]==0)],[])
boolean(lid,cyl('LID_AXIS_OPENING',48,35,[0,0,77],None,cutcol))
# One slot source with Array, then native host Boolean. They are actual through-openings.
slot=cube('SPEAKER_SLOT_SOURCE',[38,32,2.6],[0,-78,23],None,cutcol,1.25)
a=slot.modifiers.new('Four honest speaker outlets','ARRAY');a.count=4;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(0,0,7*U);boolean(cup,slot)
vent=cube('REAR_VENT_SOURCE',[30,32,1.8],[0,75,18],None,cutcol,.8)
a=vent.modifiers.new('Three rear ventilation slots','ARRAY');a.count=3;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(0,0,4.5*U);boolean(cup,vent)
usb=cube('REAR_USB_CABLE_OPENING',[13,28,8],[30,75,18],None,cutcol,1);boolean(cup,usb)
mic=cyl('FIXED_MIC_OUTLET_SOURCE',2.4,34,[-16.3,74,52],None,cutcol,'Y')
a=mic.modifiers.new('Fixed dual-mic outlets candidate coordinates','ARRAY');a.count=2;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(32.6*U,0,0);boolean(cup,mic)
statuscut=cube('STATUS_APERTURE',[8,32,1.8],[0,-78,54],None,cutcol,.8);boolean(cup,statuscut)
status=cube('STATUS_DISPLAY_REVIEW',[7.3,1,1.2],[0,-80.7,54],CORAL,presentation,.5)
buttoncut=cube('STOP_BUTTON_OPENING',[13,9,16],[0,-49,74],None,cutcol,3.8);boolean(lid,buttoncut)
button=cube('STOP_BUTTON_CAP_PROXY',[12.2,8.2,2],[0,-49,77.5],BLACK,shellcol,3.5);button['note']='actual switch travel and stem not finalized'
foot=cyl('PURCHASED_SILICONE_FOOT',156,2,[0,0,1],BLACK,hwcol);foot.scale.y=140/156
# Curved head: Y-axis Screw -> local Lattice flattening -> Solidify -> bottom trim.
# Circle remains circular at face; central/rear head is4% flattened vertically.
profile=[]
a0=math.asin((-48+8)/72);r_end=75*math.cos(a0);dr_end=-75*math.sin(a0)/(72*math.cos(a0));dy=15.6
for i in range(25):
 t=i/24;r=(2*t**3-3*t**2+1)*P['head']['front_profile_radius_mm']+(-2*t**3+3*t**2)*r_end+(t**3-t**2)*dy*dr_end
 profile.append((r,-63.6+dy*t))
for i in range(1,97):
 t=a0+(math.pi/2-a0)*i/96
 profile.append((75*math.cos(t),-8+72*math.sin(t)))
head=screw('HEAD_SHELL',profile,'Y',(0,0,150))
lat=bpy.data.lattices.new('N4_HEAD_SECTION_TRANSITION');lat.points_u=2;lat.points_v=9;lat.points_w=2;lat.interpolation_type_v='KEY_LINEAR';lat.interpolation_type_u='KEY_LINEAR';lat.interpolation_type_w='KEY_LINEAR'
lo=bpy.data.objects.new('N4_HEAD_LATTICE',lat);cutcol.objects.link(lo);lo.location=(0,0,150*U);lo.scale=(150*U,16*U,150*U);lo.hide_render=True;lo.hide_set(True);controls.append(lo)
for pt in lat.points:
 y=pt.co_deform.y*16;blend=max(0,min(1,(y+50)/25));pt.co_deform.z*=1-.04*blend
mod=head.modifiers.new('Round face to softly flattened head','LATTICE');mod.object=lo
mod=head.modifiers.new('Real nominal shell thickness','SOLIDIFY');mod.thickness=2.4*U;mod.offset=-1;mod.use_even_offset=True
trim=cube('HEAD_BOTTOM_TRIM',[500,500,300],[0,0,-58],None,cutcol);boolean(head,trim)
facebore=cyl('ROUND_FACE_RECEIVER',106.6,18,[0,-64,150],None,cutcol,'Y');boolean(head,facebore)
receiverlip,receiverlipcut=ring('FACE_RECEIVING_LIP_CONTROL',114.4,106.6,2.4,[0,-62.8,150],None,cutcol,'Y');lip_union=boolean(head,receiverlip,'UNION');lip_union.solver='MANIFOLD'
# Matte printed disk; rectangle is a real opening. Back pocket leaves1mm nominal facing rim.
face=cyl('FACE_PANEL',106,2.4,[0,-62.8,150],BLACK,axis='Y')
window=cube('REAL_LCD_APERTURE',[58.2,12,43.8],[0,-63,145],None,cutcol,.8);boolean(face,window)
pocket=cube('LCD_REAR_POCKET',[73.5,2.2,51],[0,-61.9,145],None,cutcol,.6);boolean(face,pocket)
lenshole=cyl('CAMERA_APERTURE',8.4,14,[0,-63,189],None,cutcol,'Y');boolean(face,lenshole)
# Review-only hardware glass is seated behind aperture, never covers whole disk.
glass=cube('LCD_GLASS_PROXY',[73.06,.7,50.54],[0,-62.55,145],GLASS,hwcol,.6)
lcd_spec=next(c for c in P['components'] if c['id']=='LCD')
lcdpcb=cube('LCD_PCB_PROXY',lcd_spec['body'],lcd_spec['center'],PCB,hwcol,.4)
lens=cyl('CAMERA_LENS_PROXY',7.8,3,[0,-62.8,189],GLASS,hwcol,'Y')
slider=cyl('PRIVACY_SLIDER_PROXY',9,1.7,[9,-64,189],BLACK,shellcol,'Y');slider.data.transform(Matrix.Diagonal((1.15,1,1,1)));slider['note']='needs real guide/stop/retention; blockout of open position only'
# Two expression curves are presentation only, constrained within chosen actual active area.
def pathcurve(n,pts,r,m,c=presentation):
 cu=bpy.data.curves.new('N4_'+n,'CURVE');cu.dimensions='3D';cu.resolution_u=12;cu.bevel_depth=r*U;cu.bevel_resolution=4
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for point,p in zip(sp.points,pts):point.co=(*[v*U for v in p],1)
 o=bpy.data.objects.new('N4_'+n,cu);c.objects.link(o);reg(o,n,m,c);return o
pts=[(-13+5.5*math.cos(math.pi-math.pi*i/32),-63.02,143+5.5*math.sin(math.pi-math.pi*i/32)) for i in range(33)]
eyes=pathcurve('TWO_EYES_REVIEW',pts,1.05,EYE)
a=eyes.modifiers.new('Exactly two eyes within active LCD','ARRAY');a.count=2;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(26*U,0,0)
neck,neckcut=ring('SHORT_YAW_NECK',46,22,25,[0,0,85.5],BLACK,shellcol)
# Independent purchased bearings and explicit packaging envelopes; no fake completed coupling.
for cid in ['BEARING_LOWER','BEARING_UPPER']:
 c=next(c for c in P['components'] if c['id']==cid)
 o,cut=ring(cid,42,30,7,c['center'],METAL,hwcol)
 seat,sc=ring(cid+'_SEAT_PROXY',52,42.5,10,c['center'],BLACK,supportcol);seat['note']='split-clamp carrier envelope only; screw/lip/carrying posts await sample'
shaft,shaftcut=ring('HOLLOW_SHAFT_PROXY',29.8,22,48,[0,0,69],BLACK,supportcol)
# GOOUU62.6x28.3 core fixed in rear, vertical; extension board is NOT in fit claim. Only camera module separates and rotates.
board_spec=next(c for c in P['components'] if c['id']=='MAINBOARD')
board=cube('MAINBOARD',board_spec['body'],board_spec['center'],PCB,hwcol,.5)
chip=cube('POPULATED_BOARD_KEEP_HEIGHT_PROXY',[27,7,25],[0,57.5,48],BLACK,hwcol,.6)
cam=cube('CAMERA_MODULE_PROXY',[20,10,18],[0,-53.4,188],PCB,hwcol,.3)
servo_spec=next(c for c in P['components'] if c['id']=='SERVO')
servo=cube('SERVO',servo_spec['body'],servo_spec['center'],BLUE,hwcol,.5)
speaker=cyl('SPEAKER',40,18,[0,-57,33],BLACK,hwcol,'Y')
battery=cube('BATTERY',[55,30,10],[45,4,14],BAT,hwcol,1)
for cid in ['DRIVEN_PULLEY','DRIVER_PULLEY']:
 c=next(c for c in P['components'] if c['id']==cid)
 o=cyl(cid+'_ENVELOPE',44,8.4,c['center'],BLACK,supportcol)
 boolean(o,cyl(cid+'_SHAFT_SPACE',30.2 if cid=='DRIVEN_PULLEY' else 5,14,c['center'],None,cutcol));o['note']='64T GT2 envelope only; NO fabricated spline or tooth CAD'
# Belt path is a nominal pitch curve, not a manufactured belt profile.
r=128/math.pi/2;C=50;pts=[]
for i in range(65):
 t=-math.pi/2+math.pi*i/64;pts.append((r*math.cos(t),r*math.sin(t),59.5))
for i in range(65):
 t=math.pi/2+math.pi*i/64;pts.append((-C+r*math.cos(t),r*math.sin(t),59.5))
pts.append(pts[0]);belt=pathcurve('BELT_PITCH_PATH_PROXY',pts,.9,BLACK,supportcol)
mic_spec=next(c for c in P['components'] if c['id']=='MIC_LEFT')
micboard=cube('INMP441_FIXED_SOURCE',mic_spec['body'],mic_spec['center'],PCB,hwcol,.3)
a=micboard.modifiers.new('Two stationary I2S mic modules','ARRAY');a.count=2;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(32.6*U,0,0)
for cid in ['I2S_AMP','BATTERY_CHARGER']:
 c=next(c for c in P['components'] if c['id']==cid);o=cube(cid,c['body'],c['center'],PCB,hwcol,.4);o['note']=c['confidence']
# Reserved display-bundle/camera-FPC activity volumes, NOT a validated minimum-bend or electrical route.
for c in P['components']:
 ko=cube('KEEP_OUT_'+c['id'],c['reserve'],c.get('reserve_center',c['center']),None,keepcol);ko.display_type='WIRE';ko.hide_render=True
 if c['group']=='head':headparts.append(ko)
ko=cube('DISPLAY_CAMERA_SHARED_ACTIVITY_RESERVE',[20,32,24],[0,20,117],None,keepcol);ko.display_type='WIRE';ko.hide_render=True;ko['note']='shared bay above hidden neck flange; not actual cable bend/life proof';headparts.append(ko)

# Provisional but physically connected head receiver:3.2mm floor matching the actual outer section.
# This closes the clipped bottom and provides an annular seat; not a final tolerance release.
full=screw('HEAD_RECEIVER_OUTER_CONTROL',[(0,profile[0][1])]+[(r*.999,y) for r,y in profile],'Y',(0,0,150),None,cutcol)
mod=full.modifiers.new('Same head transition owner','LATTICE');mod.object=lo
receiver=cube('HEAD_RECEIVER_FLOOR_CONTROL',[250,250,3.2],[0,0,93.6],None,cutcol)
boolean(receiver,full,'INTERSECT');boolean(head,receiver,'UNION')
receiverhole=cyl('HEAD_NECK_SEATING_HOLE',46.6,12,[0,0,93.6],None,cutcol);boolean(head,receiverhole)
flange,flangecut=ring('NECK_HIDDEN_FLANGE_CONTROL',62,22,4,[0,0,97.2],None,cutcol);boolean(neck,flange,'UNION')
# Stepped D-socket avoids former solid overlap with the30mm hollow shaft.
socket=cyl('NECK_D_SOCKET_CONTROL',30.3,21.5,[0,0,83.25],None,cutcol)
socketflat=cube('NECK_D_SOCKET_FLAT',[70,70,25],[49.2,0,83.25],None,cutcol);boolean(socket,socketflat)
boolean(neck,socket)
shaftflat=cube('SHAFT_D_FLAT_CONTROL',[70,70,21],[49,0,83.5],None,cutcol);boolean(shaft,shaftflat)
fixholes=cyl('HEAD_RECEIVER_M3_SOURCE',3.4,14,[-26,0,95],None,cutcol)
a=fixholes.modifiers.new('Two head receiver screw positions','ARRAY');a.count=2;a.use_relative_offset=False;a.use_constant_offset=True;a.constant_offset_displace=(52*U,0,0)
boolean(head,fixholes);boolean(neck,fixholes)
# Imported hardware dimensions still govern flange nuts and final fastener lengths.
extra_head=[full,receiver,receiverhole,flange,flangecut,socket,socketflat,shaft,shaftcut,shaftflat,fixholes,bpy.data.objects['N4_DRIVEN_PULLEY_ENVELOPE'],bpy.data.objects['N4_DRIVEN_PULLEY_SHAFT_SPACE']]

# Position previews are not a firmware rig. All dependent head cutters follow the same anchor.
yaw=bpy.data.objects.new('N4_YAW_LAYOUT_ANCHOR',None);shellcol.objects.link(yaw);yaw['scope']='static review pose, not firmware';yaw['nominal_yaw_limit_deg']=45
headparts += [head,lo,trim,facebore,receiverlip,receiverlipcut,face,window,pocket,lenshole,glass,lcdpcb,lens,slider,eyes,neck,neckcut,cam]+extra_head
for o in headparts:o.parent=yaw
# Store editable isolated scene, not destructive replacement of earlier scenes.
scene.world=bpy.data.worlds.new('N4_NEUTRAL_WORLD');scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.72,.75,.8,1);scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
def point(o,p):o.rotation_euler=(Vector(p)*U-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,loc,power,size,target):
 d=bpy.data.lights.new('N4_'+n,'AREA');d.energy=power;d.shape='DISK';d.size=size*U;o=bpy.data.objects.new('N4_'+n,d);presentation.objects.link(o);o.location=Vector(loc)*U;point(o,target)
light('KEY',[-320,-380,500],9,350,[0,0,110]);light('FILL',[260,-80,270],4,260,[0,0,120]);light('REAR',[100,220,330],6,200,[0,0,135])
floor=cube('GROUND',[6000,6000,2],[0,0,-1.2],material('REVIEW_GROUND',(.64,.63,.60),.85),presentation)
cameras={}
for n,loc,target,scale in [('HERO',[330,-600,280],[0,0,112],345),('FRONT',[0,-650,111],[0,0,111],335),('SIDE',[650,0,111],[0,0,111],335),('TOP',[0,0,650],[0,0,100],280),('REAR',[0,650,111],[0,0,111],335),('EXPLODED',[350,-650,350],[0,0,150],490),('INTERNAL',[350,-600,340],[0,0,107],300)]:
 d=bpy.data.cameras.new('N4_'+n);o=bpy.data.objects.new('N4_CAM_'+n,d);camcol.objects.link(o);o.location=Vector(loc)*U;point(o,target);d.type='ORTHO';d.ortho_scale=scale*U;cameras[n]=o
# Hardware/proxy visibility: keep screen/lens/foot visible, hide internal modules in assembled views.
exposed={glass.name,lens.name,foot.name}
def assembled():
 for o in hardware:o.hide_render=o.name not in exposed
 for o in supports:o.hide_render=True
 for o in shells:o.hide_render=False
 for o in presentation.objects:
  if o.type in ['CURVE','MESH']:o.hide_render=False
 yaw.rotation_euler.z=0;bpy.context.view_layer.update()
def render(n,cam):
 scene.camera=cameras[cam];scene.render.filepath=str(OUT/n);bpy.ops.render.render(write_still=True)
assembled();bpy.context.view_layer.update()
# Save before rendering, scene opens assembled and inspectors can toggle internal collections.
blend=ROOT/'EffMeet2_NOMI_布局A_工程候选_v4.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
# Evaluated shell mesh checks performed before review rendering.
def eval_stats(o):
 dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me)
 bounds=[e.matrix_world@v.co for v in me.vertices];adj={v.index:set() for v in bm.verts}
 for edge in bm.edges:
  a,b=[v.index for v in edge.verts];adj[a].add(b);adj[b].add(a)
 rem=set(adj);components=0
 while rem:
  components+=1;stack=[rem.pop()]
  while stack:
   for j in adj[stack.pop()] & rem:rem.remove(j);stack.append(j)
 stats={'vertices':len(me.vertices),'faces':len(me.polygons),'boundary_edges':sum(x.is_boundary for x in bm.edges),'nonmanifold_edges':sum(not x.is_manifold for x in bm.edges),'loose_edges':sum(x.is_wire for x in bm.edges),'zero_area_faces':sum(x.calc_area()==0 for x in bm.faces),'sub_print_scale_faces':sum(0<x.calc_area()<1e-14 for x in bm.faces),'minimum_face_area_mm2':min((x.calc_area()/U**2 for x in bm.faces),default=0),'components':components,'volume_mm3':abs(bm.calc_volume(signed=True))/U**3,'bounds_mm':[[min(v[i] for v in bounds)/U for i in range(3)],[max(v[i] for v in bounds)/U for i in range(3)]],'modifiers':[m.type for m in o.modifiers]}
 bm.free();e.to_mesh_clear();return stats
check={o.name:eval_stats(o) for o in [cup,lid,head,face,neck]}
(PROD/'evaluated-shells.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
face_bounds=check[face.name]['bounds_mm'];face_sizes=[face_bounds[1][i]-face_bounds[0][i] for i in range(3)]
assert abs(face_sizes[1]-2.4)<.05 and abs(face_sizes[2]-106)<.05,'Face panel must be vertical, not horizontal'
assert check[head.name]['bounds_mm'][1][2]<=222.05,'Head exceeds nominal222mm envelope'
# Coarse nominal profile containment; measured interfaces/lifetime excluded.
def radius(z):
 if z<4.4:return 0
 if z<20:return 72+math.sqrt(max(0,15.6**2-(z-20)**2))
 if z<=52:return 87.6
 if z<=75.6:return 64+math.sqrt(max(0,23.6**2-(z-52)**2))
 return 0
def headr(y):
 for i in range(len(profile)-1):
  r1,y1=profile[i];r2,y2=profile[i+1]
  if y1<=y<=y2:return r1+(r2-r1)*(y-y1)/(y2-y1)
 return -999
fit=[]
for c in P['components']:
 center=c.get('reserve_center',c['center']);size=c['reserve'];points=[tuple(center[i]+size[i]*s[i]/2 for i in range(3)) for s in __import__('itertools').product([-1,1],repeat=3)]
 if c['group']=='base':ok=all(radius(z)>0 and x*x+(y/(164/180))**2<radius(z)**2 for x,y,z in points)
 else:ok=all(z>=94.4 and (x*x+((z-150)/(1-.04*max(0,min(1,(y+50)/25))))**2)**.5<=headr(y)-2.4 for x,y,z in points)
 fit.append({'id':c['id'],'nominal_shell_containment':ok,'method':'conservative box corners against nominal inner radial profile; NOT fastener/FPC/hardware verification'})
(PROD/'nominal-fit.json').write_text(json.dumps({'components':fit,'all_inside':all(c['nominal_shell_containment'] for c in fit),'hardware_validated':False},indent=2),encoding='utf-8')
# Scoped yaw dependency checks cover rendered parts and their helpers, not flex dynamics.
yaw_results=[]
for deg in [-45,0,45]:
 yaw.rotation_euler.z=math.radians(deg);bpy.context.view_layer.update();s=eval_stats(head)
 yaw_results.append({'angle_deg':deg,'head_volume_mm3':s['volume_mm3'],'nonmanifold_edges':s['nonmanifold_edges'],'head_min_z':s['bounds_mm'][0][2],'shell_to_lid_min_vertical_gap_mm':s['bounds_mm'][0][2]-78})
yaw.rotation_euler.z=0;bpy.context.view_layer.update()
(PROD/'yaw-candidate-audit.json').write_text(json.dumps({'poses':yaw_results,'parented_head_objects':[o.name for o in headparts],'flex_life_validated':False},indent=2),encoding='utf-8')
# Protected object data has not changed; source blend file itself is never overwritten.
after=snap.capture_snapshot(protected);same=before['objects']==after['objects']
(PROD/'protected-scene-check.json').write_text(json.dumps({'unchanged':same,'objects_checked':len(protected),'old_scene_data_preserved':True},indent=2),encoding='utf-8')
assert same,'Pre-existing object mutation detected'
if any(s['nonmanifold_edges'] or s['loose_edges'] or s['zero_area_faces'] for s in check.values()):
 raise RuntimeError('Shell legality failure: inspect evaluated-shells.json before rendering')
render('01_hero.png','HERO');render('02_front.png','FRONT');render('03_side.png','SIDE');render('04_top.png','TOP');render('05_rear.png','REAR')
for deg,n in [(-45,'06_yaw_left.png'),(45,'07_yaw_right.png')]:
 yaw.rotation_euler.z=math.radians(deg);bpy.context.view_layer.update();render(n,'HERO')
assembled()
for o in [cup,lid,head,face]:o.hide_render=True
for o in hardware:o.hide_render=False
for o in supports:o.hide_render=False
render('08_internal_layout.png','INTERNAL')
# Exploded view is actual model separation, with proxies clearly documented in companion sheet.
assembled()
orig={o.name:o.location.copy() for o in scene.objects}
for o in headparts:o.location.z+=70*U
for o in [face,glass,lcdpcb,lens,slider,eyes,window,pocket,lenshole]:o.location.y-=75*U
lid.location.z+=32*U
for o in hardware:o.hide_render=False
for o in supports:o.hide_render=False
render('09_exploded_layout.png','EXPLODED')
for o in scene.objects:
 if o.name in orig:o.location=orig[o.name]
assembled()
# Native profile wireframe evidence without adding fake geometry to the deliverable.
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True;scene.display.shading.show_shadows=True
for o in [cup,lid,head,face]:o.show_wire=True;o.show_all_edges=True
render('10_wireframe.png','HERO')
for o in [cup,lid,head,face]:o.show_wire=False
scene.render.engine='CYCLES';scene.camera=cameras['HERO'];scene.render.filepath=str(OUT/'01_hero.png')
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
print(json.dumps({'model':str(blend),'renders':str(OUT),'shell_meshes':'PASS','nominal_fit':all(c['nominal_shell_containment'] for c in fit),'manufacturing_ready':False,'hardware_validated':False}))
