"""v6 compact candidate (layout A2: core board + camera in head; mics/amp/speaker/servo/key in base).
Fresh scene N6_COMPACT_CANDIDATE built from parameters below. Native Screw/Boolean/Lattice/Solidify kept.
Never touches v4/v5 scenes or files. All status booleans stay False. Proxies/KEEP_OUT never printed.
Run: blender -b <v2.blend> --python build_v6.py
"""
import bpy,bmesh,json,math,os
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent;PROD=ROOT/'production';REN=ROOT/'renders';U=.001
for d in (PROD,REN):d.mkdir(exist_ok=True)
K=.85
PARAMS=dict(
 base_scale=K,base_y_scale=164/180,wall=2.4,bottom=2.4,
 cup_top_z=66*K,lid_top_z=78*K,lid_seam_z=66.3*K,
 head_gap_above_lid=14,head_R=66,head_B=64,head_yc=-1,head_front_r=57,head_front_y=-47.0,head_junction_y=-31.0,
 head_trim_below_center=56,head_offset_y=20,head_flatten=.04,head_wall=2.4,head_floor=3.2,
 face_d=106,face_t=2.4,face_y=-46.2,lcd_window=(58.2,43.8),lcd_window_dz=-2,camera_above_window=17,glass_pocket=(71,1.4,51),backstop=(112,102,2),
 lcd_pcb=(85,1.6,50),lcd_stack=11,lcd_glass=(69,.7,50),lcd_boss_rect=(77,45),  # 2026-10-15 measured (was 80x45 assumed)
 board=(28.3,1.6,62.6),board_comp=6,board_pins=8,camera_module=(8,4,8),camera_fpc=14,camera_recess=4.5,camera_lens_d=6.5,camera_fpc_max_span=11,usb_access=10,dupont_clear=12,
 gt2_pitch=2.0,driver_T=32,driven_T=64,belt_candidates=(158,160,180,188,200),belt_w=6,
 bearing=(30,42,7),bearing_z=(36.5,56.5),lower_seat_z=(32,40.6),upper_seat_z=(52,60.6),pulley_z=46.4,pulley_h=8.4,flange_t=1.2,seat_h=7.6,seat_od=54,seat_bore=42.3,lip_id=38.5,bolt_xy=((26,22),(26,-22),(-22,27),(-22,-27)),
 shaft=(29.8,22),shaft_z=(26,86),shoulder=(34.5,60,61.4),collar=(36,30.15,27,32.8),neck_od=40,neck_spigot=35,neck_bottom=64.4,stop_arm_z=(61.8,63.6),flange_d=58,flange_h=4,neck_screw_x=24,lid_axis_hole=44,
 stop_soft=45,stop_contact=48,
 servo_body=(12.5,22.4,22.7),servo_ear_len=31.8,servo_ear_pitch=27.7,servo_ear_z=(19.8,22.8),servo_h_horn=32.9,servo_horn=(31.2,4.72),servo_shaft_from_end=6.0,servo_tension=2,
 mic_d=14,mic_h=12,mic_pitch=32.6,mic_z=46,mic_x=16.3,amp=(17.7,19.1),amp_xy=(50,0),amp_floor=14,amp_hole_pitch=12.6,power_z=30,vent_x=30,speaker=(40,17),speaker_z=30,speaker_front_y=-57,servo_base_z=8.3,
 power_board=(20,15,6),key_xy=(0,-44),cable_keepout_d=10,
)
P=PARAMS
src=bpy.context.scene
scene=bpy.data.scenes.new('N6_COMPACT_CANDIDATE');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
def col(n):
 c=bpy.data.collections.new('N6_'+n);scene.collection.children.link(c);return c
SH=col('SHELLS');PARTS=col('PRINTED_PARTS');CTRL=col('NATIVE_CONTROLS');PROX=col('COMPONENT_PROXIES');KEEP=col('KEEP_OUTS');CAMS=col('CAMERAS');PRES=col('REVIEW_ONLY')
def material(n,c,rough=.65,metal=0,emission=0):
 m=bpy.data.materials.new('N6_'+n);m.diffuse_color=(*c,1);m.use_nodes=True;bs=next(x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if emission:bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=emission
 return m
GREY=material('PLA_GREY_PREVIEW',(.63,.65,.66),.72);BLACK=material('PLA_BLACK_PREVIEW',(.018,.021,.024),.68)
GLASS=material('LCD_GLASS',(.012,.016,.022),.23);PCB=material('PCB_PROXY',(.06,.25,.20),.62);METAL=material('METAL_PROXY',(.4,.43,.47),.3,.65)
BLUE=material('SERVO_PROXY',(.15,.31,.44),.55);CABLE=material('CABLE_PROXY',(.62,.35,.11),.6);EYE=material('WARM_DISPLAY',(1,.79,.52),.4,1.4)
parts=[];proxies=[];keepouts=[];rotating=set();controls=[]
def link(o,c):
 for a in list(o.users_collection):a.objects.unlink(o)
 c.objects.link(o);return o
def obj(n,verts,faces,center=(0,0,0),c=None,mat=None):
 me=bpy.data.meshes.new('N6_'+n+'_MESH');me.from_pydata([[v*U for v in p] for p in verts],[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new('N6_'+n,me);(c or CTRL).objects.link(o);o.location=Vector(center)*U
 if mat:me.materials.append(mat)
 if (c or CTRL)==CTRL:controls.append(o);o.hide_render=True;o.hide_set(True);o.display_type='WIRE'
 return o
def box(n,size,center,c=None,mat=None,bevel=0):
 x,y,z=[v/2 for v in size];v=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)];f=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
 o=obj(n,v,f,center,c,mat)
 if bevel:m=o.modifiers.new('Edge radius','BEVEL');m.width=bevel*U;m.segments=3;m.limit_method='ANGLE'
 return o
def cylinder(n,d,h,center,axis='Z',c=None,mat=None,segments=64):
 r=d/2;v=[(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),z*h/2) for z in (-1,1) for i in range(segments)]
 f=[tuple(range(segments-1,-1,-1)),tuple(range(segments,2*segments))]+[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
 o=obj(n,v,f,center,c,mat)
 if axis=='Y':o.data.transform(Matrix.Rotation(math.pi/2,4,'X'))
 if axis=='X':o.data.transform(Matrix.Rotation(math.pi/2,4,'Y'))
 return o
def boolop(host,cut,op='DIFFERENCE',solver='MANIFOLD'):
 m=host.modifiers.new(op+' '+cut.name,'BOOLEAN');m.operation=op;m.solver=solver;m.object=cut;return m
def unite(host,piece,solver='MANIFOLD'):return boolop(host,piece,'UNION',solver)
def hole(host,center,d=3.4,depth=60,axis='Z',solver='MANIFOLD'):
 return boolop(host,cylinder(host.name[3:]+'_HOLE_'+str(len(host.modifiers)),d,depth,center,axis),solver=solver)
def ring(n,od,idd,h,center,axis='Z',c=None,mat=None):
 o=cylinder(n,od,h,center,axis,c,mat);hole(o,center,idd,h+4,axis);return o
def hexhole(host,center,flat=5.7,depth=2.6,axis='Z'):
 return boolop(host,cylinder(host.name[3:]+'_NUT_'+str(len(host.modifiers)),flat/math.cos(math.pi/6),depth,center,axis,segments=6))
def part(o,cn,mat=BLACK,motion=False,function=''):
 link(o,PARTS);o.hide_render=False
 if mat and not o.data.materials:o.data.materials.append(mat)
 o['interface_status']='unverified';o['manufacturing_ready']=False;o['hardware_validated']=False;o['stage']='reversible_blockout'
 parts.append({'id':f'P{len(parts)+1:02d}','name':cn,'object':o.name,'rotating':motion,'function':function or cn})
 if motion:rotating.add(o.name)
 return o
def proxy(o,n,motion=False,mat=PCB,note='budget, UNVERIFIED'):
 link(o,PROX);o.hide_render=False;o['actual_product_CAD']=False;o['note']=note;o['never_printed']=True
 if mat and not o.data.materials:o.data.materials.append(mat)
 proxies.append({'name':o.name,'label':n,'rotating':motion,'note':note})
 if motion:rotating.add(o.name)
 return o
def keepout(o,motion=False,note='keep-out'):
 link(o,KEEP);o.hide_render=True;o.display_type='WIRE';o['never_printed']=True;o['note']=note;keepouts.append(o.name)
 if motion:rotating.add(o.name)
 return o
def screw(n,profile,axis='Z',center=(0,0,0),c=None,mat=GREY,closed=False):
 coords=[(r*U,0,z*U) if axis=='Z' else (r*U,z*U,0) for r,z in profile];N=len(coords)
 edges=[(i,(i+1)%N) for i in range(N if closed else N-1) if not(closed and profile[i][0]==0 and profile[(i+1)%N][0]==0)]
 me=bpy.data.meshes.new('N6_'+n+'_PROFILE');me.from_pydata(coords,edges,[]);me.update()
 o=bpy.data.objects.new('N6_'+n,me);(c or SH).objects.link(o);o.location=Vector(center)*U
 if mat:me.materials.append(mat)
 m=o.modifiers.new('Editable radial section','SCREW');m.axis=axis;m.angle=2*math.pi;m.steps=128;m.render_steps=128;m.use_merge_vertices=True;m.merge_threshold=1e-6;m.use_smooth_shade=True;m.use_normal_calculate=True
 o['native_owner']='SCREW'
 if (c or SH)==CTRL:controls.append(o);o.hide_render=True;o.hide_set(True);o.display_type='WIRE'
 return o
def arc(cr,cz,r,a,b,n=28):return [(cr+r*math.cos(a+(b-a)*i/n),cz+r*math.sin(a+(b-a)*i/n)) for i in range(n+1)]
yaw=bpy.data.objects.new('N6_YAW_LAYOUT_ANCHOR',None);SH.objects.link(yaw);yaw['scope']='static review pose, not firmware'
print('STAGE helpers ok',flush=True)
#@@SHELLS@@
# ---------- BASE: v4 cup/lid profiles scaled radially+height (K), true 2.4 wall kept ----------
k=P['base_scale'];W=P['wall'];zb=2;r0=72*k;fr=18*k;zf=zb+fr;rmax=r0+fr;zs=52*k;cr=64*k;R2=26*k;zt=P['cup_top_z'];zl=zt+.3;P['lid_seam_z']=zl;ztop=zs+R2;P['lid_top_z']=ztop
a=math.asin((zt-zs)/R2);ai=math.asin((zt-zs)/(R2-W))
cp=[(0,zb),(r0,zb)]+arc(r0,zf,fr,-math.pi/2,0)[1:]+[(rmax,zs)]+arc(cr,zs,R2,0,a)[1:]+arc(cr,zs,R2-W,ai,0)+[(rmax-W,zf)]+arc(r0,zf,fr-W,0,-math.pi/2)[1:]+[(0,zb+W)]
cup=screw('BASE_CUP',cp,closed=True);cup.scale.y=P['base_y_scale']
al=math.asin((zl-zs)/R2);ail=math.asin((zl-zs)/(R2-W))
lp=arc(cr,zs,R2,al,math.pi/2)+[(0,ztop),(0,ztop-W),(cr,ztop-W)]+arc(cr,zs,R2-W,math.pi/2,ail)[1:]
lid=screw('BASE_LID',lp,closed=True);lid.scale.y=P['base_y_scale']
P['base_outer_mm']=[2*rmax,2*rmax*P['base_y_scale'],ztop];P['lid_inner_top_z']=ztop-W;P['base_inner_floor_z']=zb+W
def base_inner_r(z):
 if z<zb+W:return 0
 if z<zf:return r0+math.sqrt(max(0,(fr-W)**2-(z-zf)**2))
 if z<=zs:return rmax-W
 return cr+math.sqrt(max(0,(R2-W)**2-(z-zs)**2))
oc=[(0,zb),(r0,zb)]+arc(r0,zf,fr,-math.pi/2,0)[1:]+[(rmax,zs)]+arc(cr,zs,R2,0,a)[1:]+[(0,zt)]
cupclip=screw('CUP_OUTER_CLIP',oc,c=CTRL,mat=None,closed=True);cupclip.scale.y=P['base_y_scale']
lc=[(0,zl)]+arc(cr,zs,R2,al,math.pi/2)+[(0,ztop)]
lidclip=screw('LID_OUTER_CLIP',lc,c=CTRL,mat=None,closed=True);lidclip.scale.y=P['base_y_scale']
EX='EXACT'
slot=box('SPEAKER_SLOT_SOURCE',(30,34,2.6),(0,-70,P['speaker_z']-10.5),bevel=1.2)
m=slot.modifiers.new('Four speaker outlets','ARRAY');m.count=4;m.use_relative_offset=False;m.use_constant_offset=True;m.constant_offset_displace=(0,0,7*U);boolop(cup,slot,solver=EX)
vent=box('REAR_VENT_SOURCE',(20,34,1.8),(P['vent_x'],62,24),bevel=.8)
m=vent.modifiers.new('Three rear vents','ARRAY');m.count=3;m.use_relative_offset=False;m.use_constant_offset=True;m.constant_offset_displace=(0,0,4.2*U);boolop(cup,vent,solver=EX)
PB=P['power_board'];pbz=P['power_z']
usb=box('REAR_USBC_POWER_OPENING',(13.5,30,9.5),(0,70,pbz),bevel=1)  # 2026-10-15 tolerant window, SKU-independent;boolop(cup,usb,solver=EX)
mx=P['mic_x'];mz=P['mic_z']
micport=cylinder('MIC_PORT_SOURCE',2.4,30,(-mx,70,mz),'Y')
m=micport.modifiers.new('Two fixed mic ports','ARRAY');m.count=2;m.use_relative_offset=False;m.use_constant_offset=True;m.constant_offset_displace=(2*mx*U,0,0);boolop(cup,micport,solver=EX)
stat=box('STATUS_APERTURE',(7,34,1.6),(0,-70,zt-4),bevel=.6);boolop(cup,stat,solver=EX)
print('STAGE cup cutters',flush=True)
#@@BASE2@@
boolop(lid,cylinder('LID_AXIS_OPENING',P['lid_axis_hole'],30,(0,0,ztop)),solver=EX)
kx,ky=P['key_xy']
boolop(lid,box('STOP_BUTTON_OPENING',(13,9,12),(kx,ky,ztop),bevel=2.5),solver=EX)
# Cover screws: cup receiver bosses fused to wall and clipped to native outer; lid receivers clipped to lid outer.
COVER=[(sx*48,sy*42) for sx in (-1,1) for sy in (-1,1)]
for x,y in COVER:
 b=cylinder(f'COVER_CUP_BOSS_{x}_{y}',10,10,(x,y,zt-5));ang=math.atan2(y/P['base_y_scale'],x)
 rib=box(f'COVER_CUP_RIB_{x}_{y}',(12,8,10),(x+5*math.cos(ang),y+5*math.sin(ang),zt-5));rib.rotation_euler.z=ang;unite(b,rib);boolop(b,cupclip,'INTERSECT');unite(cup,b)
 hole(cup,(x,y,zt-5),2.5,14);r=cylinder(f'COVER_LID_RECEIVER_{x}_{y}',8,8,(x,y,zl+4));boolop(r,lidclip,'INTERSECT',solver=EX);unite(lid,r,solver=EX);hole(lid,(x,y,zl+4),3.4,20,solver=EX)
# Bearing-tower and servo-cradle floor fixings: M3 into captive nuts under cup floor.
def floor_fix(x,y):
 hole(cup,(x,y,zb+W/2),3.4,10);hexhole(cup,(x,y,zb+1.0),5.7,2.0)
def floor_screw_up(host,x,y,slot=0):
 if slot:boolop(cup,box(f'CUP_SLOT_{x}_{y}',(3.4+2*slot,3.4,10),(x,y,zb+W/2),bevel=1.6));boolop(cup,box(f'CUP_SLOT_CB_{x}_{y}',(6.2+2*slot,6.2,1.2),(x,y,zb+.6),bevel=3))
 else:hole(cup,(x,y,zb+W/2),3.4,10);hole(cup,(x,y,zb+.6),6.2,1.2)
 hole(host,(x,y,fl+5),2.6,10)
# Mic wall pockets (fixed, rear-top) and two retainer bosses tied to wall.
def wall_y(z,x=0):
 r=base_inner_r(z);return P['base_y_scale']*math.sqrt(max(0,r*r-x*x))
mwy=min(wall_y(mz+dz,mx+dx) for dx in (-7,0,7) for dz in (-7,0,7));P['mic_wall_y']=mwy
for sx in (-1,1):
 ring_=ring(f'MIC_WALL_POCKET_{sx}',18,14.6,16,(sx*mx,mwy-1,mz),'Y');boolop(ring_,cupclip,'INTERSECT');unite(cup,ring_)
part(cup,'底座杯体（原生Screw剖面×0.85）',GREY)
part(lid,'底座上盖＋限位块',GREY)
print('STAGE base shells',flush=True)
#@@DRIVE@@
# ---------- DRIVE 2:1 GT2 ----------
pd=lambda T:T*P['gt2_pitch']/math.pi
D=pd(P['driven_T']);d=pd(P['driver_T']);P['pitch_D']=D;P['pitch_d']=d
def C_for(L):
 c=(L-math.pi*(D+d)/2)/2
 for _ in range(30):c=(L-math.pi*(D+d)/2-(D-d)**2/(4*c))/2
 return c
Cmin=44.5;belts=[{'L':L,'C':round(C_for(L),3)} for L in P['belt_candidates']]
pick=min((b for b in belts if b['C']>=Cmin),key=lambda b:b['C']);CC=pick['C'];P['belt_pick']=pick;P['belt_table']=belts;P['C_min_clearance']=Cmin
Lchk=2*CC+math.pi*(D+d)/2+(D-d)**2/(4*CC);P['belt_L_check']=Lchk
pz=P['pulley_z'];ph=P['pulley_h'];ft=P['flange_t'];bz0,bz1=P['bearing_z'];BW=P['bearing'][2]
def toothed(n,T,cx,rot):
 pdia=pd(T);od=pdia-.508;w=cylinder(n,od,ph,(cx,0,pz))
 for zz in (pz-ph/2-ft/2+.1,pz+ph/2+ft/2-.1):unite(w,cylinder(n+'_FLANGE_'+str(round(zz,1)),od+3,ft,(cx,0,zz)))
 rg=od/2-.0;g=cylinder(n+'_GROOVE_SOURCE',1.5,ph+.4,(cx,0,pz),segments=16);g.data.transform(Matrix.Translation((rg*U,0,0)))
 e=bpy.data.objects.new('N6_'+n+'_RADIAL_ARRAY_CONTROL',None);CTRL.objects.link(e);controls.append(e);e.location=(cx*U,0,pz*U);e.rotation_euler.z=2*math.pi/T;e.hide_render=True
 a=g.modifiers.new(f'{T} radial tooth valleys candidate','ARRAY');a.count=T;a.use_relative_offset=False;a.use_object_offset=True;a.offset_object=e;boolop(w,g)
 w['tooth_profile_status']='rounded-groove hypothesis; NOT certified GT2';return w
dw=toothed('DRIVEN_64T',64,0,True);hole(dw,(0,0,pz),P['collar'][1],20);hole(dw,(14,0,pz),2.8,16,'X');hexhole(dw,(15.6,0,pz),5.7,2.5,'X')
part(dw,'从动64T带轮（套空心轴＋M3顶丝）',motion=True)
SX=-CC;hz=P['servo_base_z']+P['servo_h_horn']
drv=toothed('DRIVER_32T',32,SX,False);hub0=hz-2;hub1=pz-ph/2-ft+.6;unite(drv,cylinder('DRIVER_HORN_HUB',34,hub1-hub0,(SX,0,(hub0+hub1)/2)))
boolop(drv,box('DRIVER_HORN_POCKET',(P['servo_horn'][1]+.6,P['servo_horn'][0]+.6,2.4),(SX,0,hz-1.0),bevel=1.5));hole(drv,(SX,0,pz),5.6,30)
part(drv,'舵机主动32T带轮＋双臂舵盘口袋')
# Bearing tower + integrated lower seat, upper seat, spacers. Fixed set.
so=P['seat_od'];sb=P['seat_bore'];li=P['lip_id']
l0,l1=P['lower_seat_z'];u0,u1=P['upper_seat_z'];fl=P['base_inner_floor_z']
tower=ring('BEARING_TOWER_LOWER_SEAT',so,sb,l1-l0,(0,0,(l0+l1)/2))
unite(tower,ring('LOWER_SEAT_LIP',so,li,1,(0,0,l0+.5)))
for i,(x,y) in enumerate(P['bolt_xy']):
 ang=math.atan2(y,x);rr=math.hypot(x,y)
 ear=box(f'LOWER_EAR_{i}',(rr-so/2+6,10,l1-l0),((rr+so/2-6)/2*math.cos(ang),(rr+so/2-6)/2*math.sin(ang),(l0+l1)/2));ear.rotation_euler.z=ang;unite(tower,ear)
 unite(tower,box(f'TOWER_COLUMN_{i}',(10,10,l1-fl),(x,y,(l1+fl)/2),bevel=.5));unite(tower,box(f'TOWER_FOOT_{i}',(16,16,3),(x,y,fl+1.5),bevel=.5))
 hole(tower,(x,y,30),3.4,80);floor_fix(x,y)
boolop(tower,cylinder('TOWER_SEAT_INNER_CLEAR',sb,l1-l0-1,(0,0,(l0+1+l1)/2+.01)))
part(tower,'承力塔＋下轴承座（一体，四柱落底）')
up=ring('UPPER_BEARING_SEAT',so,sb,u1-u0,(0,0,(u0+u1)/2));unite(up,ring('UPPER_SEAT_LIP',so,li,1,(0,0,u0+.5)))
for i,(x,y) in enumerate(P['bolt_xy']):
 ang=math.atan2(y,x);rr=math.hypot(x,y)
 ear=box(f'UPPER_EAR_{i}',(rr-so/2+6,10,u1-u0),((rr+so/2-6)/2*math.cos(ang),(rr+so/2-6)/2*math.sin(ang),(u0+u1)/2));ear.rotation_euler.z=ang;unite(up,ear)
 unite(up,cylinder(f'UPPER_EAR_PAD_{i}',10,u1-u0,(x,y,(u0+u1)/2)));hole(up,(x,y,u0),3.4,40);hexhole(up,(x,y,u1-1.2),5.7,2.6)
boolop(up,cylinder('UPPER_SEAT_INNER_CLEAR',sb,u1-u0-1,(0,0,(u0+1+u1)/2+.01)))
part(up,'上轴承座（4×M3贯穿压紧）')
for i,(x,y) in enumerate(P['bolt_xy']):part(ring(f'STACK_SPACER_{i}',8.2,3.4,u0-l1,(x,y,(u0+l1)/2)),f'轴承层间支柱{i+1}')
print('STAGE drive',flush=True)
#@@SHAFT@@
# ---------- SHAFT / COLLAR / STOP ARM / D-flats (rotating) ----------
s0,s1=P['shaft_z'];sod,sid=P['shaft'];so_,sz0,sz1=P['shoulder']
shaft=ring('HOLLOW_LOAD_SHAFT',sod,sid,s1-s0,(0,0,(s0+s1)/2));unite(shaft,ring('SHAFT_SHOULDER',so_,sid,sz1-sz0,(0,0,(sz0+sz1)/2)))
for n,x,z0,z1 in (('DRIVE',14.2,pz-ph/2,pz+ph/2),('UPPER',14.0,P['stop_arm_z'][0],s1+1)):boolop(shaft,box('SHAFT_'+n+'_D',(30,40,z1-z0),(x+15,0,(z0+z1)/2)))
part(shaft,'空心承力轴 Ø29.8/22（轴肩＋两段D面）',motion=True)
dkey=box('DRIVEN_D_FLAT_FILL',(1.9,30,ph),(15.2,0,pz));boolop(dkey,cylinder('DRIVEN_D_FILL_CLIP',30.6,ph+1,(0,0,pz)),'INTERSECT');unite(dw,dkey);hole(dw,(14,0,pz),2.8,16,'X')
cz0,cz1=P['collar'][2],P['collar'][3];collar=ring('SHAFT_LOWER_LOCK_COLLAR',P['collar'][0],P['collar'][1],cz1-cz0,(0,0,(cz0+cz1)/2))
for x in (-4.5,4.5):unite(collar,box('COLLAR_EAR_'+str(x),(6,9,6.5),(x,-20,28.25)))
boolop(collar,box('COLLAR_SPLIT',(.8,30,10),(0,-22,(cz0+cz1)/2)));hole(collar,(0,-21,28.25),2.4,20,'X')
part(collar,'空心轴下止推夹环',motion=True)
a0z,a1z=P['stop_arm_z'];arm=ring('YAW_STOP_ARM',36,30.15,a1z-a0z,(0,0,(a0z+a1z)/2))
unite(arm,box('YAW_STOP_LUG',(16,6,a1z-a0z),(25,0,(a0z+a1z)/2),bevel=.6))
fill=box('STOP_ARM_D_FILL',(1.9,30,a1z-a0z),(15.0,0,(a0z+a1z)/2));boolop(fill,cylinder('STOP_ARM_D_CLIP',30.6,4,(0,0,(a0z+a1z)/2)),'INTERSECT');unite(arm,fill)
part(arm,'限位摆臂（D孔，硬限位48°）',motion=True)
lug_half=math.degrees(math.asin(3/29));stop_c=P['stop_contact']+2*lug_half;P['fixed_stop_center_deg']=stop_c
lit=P['lid_inner_top_z']
for sg in (-1,1):
 an=math.radians(sg*stop_c);st=box(f'FIXED_YAW_STOP_{sg}',(10,6,lit-a0z+.6+.2),(29*math.cos(an),29*math.sin(an),(lit+.6+a0z-.4)/2));st.rotation_euler.z=an;unite(lid,st)
# Neck: bottom spigot through lid hole and head floor, flange inside head, D-socket on shaft.
hc=P['lid_top_z']+P['head_gap_above_lid']+P['head_trim_below_center'];P['head_center_z']=hc
hb=hc-P['head_trim_below_center'];hft=hb+P['head_floor'];P['head_bottom_z']=hb;P['head_floor_top_z']=hft
nb=P['neck_bottom'];fh=P['flange_h']
neck=ring('SHORT_YAW_NECK',P['neck_od'],sid,hft+1-nb,(0,0,(nb+hft+1)/2));unite(neck,ring('NECK_FLANGE',P['flange_d'],sid,fh,(0,0,hft+fh/2)))
sock=cylinder('NECK_D_SOCKET',30.3,s1-nb+.01,(0,0,(nb+s1)/2-.005));boolop(sock,box('NECK_SOCKET_FLAT',(30,40,40),(14.15+15,0,(nb+s1)/2)));boolop(neck,sock)
for x in (-P['neck_screw_x'],P['neck_screw_x']):hole(neck,(x,0,hft),3.4,30);hexhole(neck,(x,0,hft+fh-1.2),5.7,2.6)
part(neck,'短颈＋法兰（D孔套轴）',motion=True)
print('STAGE shaft neck hc=%.1f'%hc,flush=True)
#@@SERVO@@
# ---------- SERVO cradle (fixed), ±2 mm tension slots along belt axis ----------
sb_=P['servo_body'];sbz=P['servo_base_z'];SCX=SX-(sb_[1]/2-P['servo_shaft_from_end']);P['servo_center_x']=SCX
ez0=sbz+P['servo_ear_z'][0];ez1=sbz+P['servo_ear_z'][1];tn=P['servo_tension']
sv=box('SERVO_ADJUSTABLE_CRADLE',(24,24,3),(SCX+5,0,fl+1.5),bevel=.5)
wy=sb_[0]/2+.6+1.5
for dy in (-1,1):
 unite(sv,box(f'SERVO_WALL_LOW_{dy}',(24,3,ez0-fl),(SCX+5,dy*wy,(ez0+fl)/2)))
 unite(sv,box(f'SERVO_WALL_HIGH_{dy}',(36,3,8),(SCX,dy*wy,ez0-4)))
for dx in (-1,1):
 rx=SCX+dx*P['servo_ear_pitch']/2
 unite(sv,box(f'SERVO_EAR_PAD_{dx}',(8,2*wy+3,3),(rx,0,ez0-1.5),bevel=.5))
 boolop(sv,box(f'SERVO_EAR_PILOT_SLOT_{dx}',(1.8+2*tn,1.8,8),(rx,0,ez0-1.5),bevel=.8))
boolop(sv,box('SERVO_BODY_POCKET',(sb_[1]+1.2,sb_[0]+1.2,40),(SCX,0,sbz+20)))
for x in (SCX+5-8,SCX+5+8):floor_screw_up(sv,x,0,slot=tn)
part(sv,'MG90S舵机可调耳架（±2张紧槽）')
# ---------- speaker cradle (front), amp tray, power-input tray, mic pocket retainers ----------
spd,spl=P['speaker'];spz=P['speaker_z'];spy=P['speaker_front_y']+spl/2
sp=ring('SPEAKER_CRADLE',46,40.6,spl+1,(0,spy,spz),'Y');unite(sp,ring('SPEAKER_REAR_LIP',45.2,36,1.6,(0,spy+spl/2+1.1-.2,spz),'Y'))
for x in (-15,15):unite(sp,box(f'SPEAKER_LEG_{x}',(6,8,spz-20-fl+3),(x,spy,(spz-17+fl)/2)));floor_screw_up(sp,x,spy)
part(sp,'扬声器圆筒托架（≤46宽）')
ax,ay=P['amp_xy'];aw,ad=P['amp'];af=P['amp_floor'];aph=P['amp_hole_pitch']
amp_t=box('AMP_LOW_TRAY',(aw+5,ad+5,2),(ax,ay,af-1),bevel=.6);unite(amp_t,box('AMP_TRAY_WALL',(aw+5,ad+5,2.5),(ax,ay,af+.75)));unite(amp_t,box('AMP_PEDESTAL',(12,12,af-2-fl+.4),(ax,ay,(af-2+fl)/2+.2)))
boolop(amp_t,box('AMP_BOARD_POCKET',(aw+.6,ad+.6,3),(ax,ay,af+1.5)))
for sx in (-1,1):
 unite(amp_t,cylinder(f'AMP_POST_{sx}',4.5,2.9,(ax+sx*aph/2,ay,af+1.05)))
 hole(amp_t,(ax+sx*aph/2,ay,af+1.2),1.7,6)
floor_screw_up(amp_t,ax,ay)
part(amp_t,'MAX98357A低托盘')
pbw,pbd,pbh=PB;pby=wall_y(pbz)-pbd/2-1.5;P['power_board_y']=pby
pt=pbz-pbh/2;pw=box('POWER_IN_TRAY',(pbw+5,pbd,3),(0,pby,pt-1.5),bevel=.6);unite(pw,box('POWER_PEDESTAL',(12,6,pt-3-fl+.4),(0,pby-5,(pt-3+fl)/2+.2)))
for x in (-pbw/2-1.5,pbw/2+1.5):unite(pw,box(f'POWER_SIDE_{x}',(2,pbd,pbh),(x,pby,pbz)))
floor_screw_up(pw,0,pby-5)
part(pw,'USB-C 5V输入板托架（预算件）')
key=box('STOP_KEY_CAP',(12.2,8.2,2),(kx,ky,ztop+.6),bevel=1.5);unite(key,box('STOP_KEY_STEM',(4,4,ztop-lit+2.3),(kx,ky,(ztop+lit-2.3)/2)));unite(key,box('STOP_KEY_FOOT',(15,10.4,1.2),(kx,ky,lit-.65)))
part(key,'停止键帽＋键柱')
kh=box('TACTILE_HOLDER',(36,14,3),(kx,ky,lit-8.3),bevel=.5);boolop(kh,box('TACT_6MM_POCKET',(6.4,6.4,4),(kx,ky,lit-6.9)))
for x in (-14,14):unite(kh,cylinder(f'KEY_STANDOFF_{x}',7,5.6+.2,(x,ky,lit-4.0-.1)));unite(lid,cylinder(f'KEY_RECEIVER_{x}',7,1.21,(x,ky,lit-.6)));hole(kh,(x,ky,lit-4),2.6,12);hole(lid,(x,ky,lit),2.6,4)
part(kh,'轻触开关托座')
for sx in (-1,1):
 mr=ring(f'MIC_RETAINER_{sx}',14.4,10,1,(sx*mx,mwy-4.2,mz),'Y');part(mr,f'麦克风压圈{"左右"[sx>0]}（胶固定于壁袋）')
print('STAGE base electronics',flush=True)
#@@HEAD@@
# ---------- HEAD: Y-axis Screw (front r57 -> ellipsoid R/B) + Lattice flatten + Solidify + trims ----------
HR,HB,yc=P['head_R'],P['head_B'],P['head_yc'];fy=P['head_front_y'];jy=P['head_junction_y'];fr57=P['head_front_r']
a0=math.asin((jy-yc)/HB);r_end=HR*math.cos(a0);dr_end=-HR*math.sin(a0)/(HB*math.cos(a0));dyy=jy-fy;prof=[]
for i in range(25):
 t=i/24;prof.append(((2*t**3-3*t**2+1)*fr57+(-2*t**3+3*t**2)*r_end+(t**3-t**2)*dyy*dr_end,fy+dyy*t))
for i in range(1,97):
 t=a0+(math.pi/2-a0)*i/96;prof.append((HR*math.cos(t),yc+HB*math.sin(t)))
P['head_profile_y']=[fy,yc+HB]
head=screw('HEAD_SHELL',prof,'Y',(0,0,hc))
lat=bpy.data.lattices.new('N6_HEAD_FLATTEN');lat.points_u=2;lat.points_v=9;lat.points_w=2
lo=bpy.data.objects.new('N6_HEAD_LATTICE',lat);CTRL.objects.link(lo);controls.append(lo);lo.location=(0,yc*U,hc*U);lo.scale=(160*U,(HB*2+60)*U,160*U);lo.hide_render=True
for pt in lat.points:
 y=yc+pt.co_deform.y*(HB*2+60);bl=max(0,min(1,(y-jy)/25));pt.co_deform.z*=1-P['head_flatten']*bl
def flat(o):m=o.modifiers.new('Round face to softly flattened head','LATTICE');m.object=lo
flat(head);m=head.modifiers.new('Real nominal shell thickness','SOLIDIFY');m.thickness=P['head_wall']*U;m.offset=-1;m.use_even_offset=True
full=screw('HEAD_OUTER_CONTROL',[(0,prof[0][1])]+[(r*.999,y) for r,y in prof]+[(0,prof[-1][1])],'Y',(0,0,hc),c=CTRL,mat=None);flat(full)
trim=box('HEAD_BOTTOM_TRIM',(400,400,200),(0,0,hb-100));boolop(head,trim,solver=EX)
rec=box('HEAD_FLOOR_SLAB',(250,250,P['head_floor']),(0,0,hb+P['head_floor']/2));boolop(rec,full,'INTERSECT',solver=EX);boolop(head,rec,'UNION',solver=EX)
boolop(head,cylinder('HEAD_NECK_HOLE',P['neck_od']+.6,12,(0,0,hb+1)),solver=EX)
for x in (-P['neck_screw_x'],P['neck_screw_x']):hole(head,(x,0,hb+1),3.4,10,solver=EX)
fy0=P['face_y'];ft_=P['face_t']
boolop(head,cylinder('ROUND_FACE_RECEIVER',P['face_d']+.6,20,(0,fy0-8,hc),'Y'),solver=EX)
lip=ring('FACE_RECEIVING_LIP',P['face_d']+8.4,P['face_d']+.6,2.4,(0,fy0+ft_/2+1.2,hc),'Y');boolop(lip,full,'INTERSECT');unite(head,lip,solver=EX)
part(head,'头壳（原生Screw＋Lattice＋Solidify）',GREY,motion=True)
# head cable saddle receiver boss on floor
hsx,hsy=0,-36;unite(head,cylinder('HEAD_SADDLE_BOSS',8,3.6,(hsx,hsy,hft+1.2)),solver=EX);hole(head,(hsx,hsy,hft),2.6,12,solver=EX)
print('STAGE head shell',flush=True)
#@@FACE@@
# ---------- FACE + LCD + CAMERA + CORE BOARD (all rotate) ----------
fb=fy0+ft_/2;wz=hc+P['lcd_window_dz'];ww,wh=P['lcd_window'];cz=wz+wh/2+P['camera_above_window'];P['camera_z']=cz
face=cylinder('FACE_PANEL',P['face_d'],ft_,(0,fy0,hc),'Y',segments=128)
boolop(face,box('LCD_WINDOW',(ww,12,wh),(0,fy0,wz),bevel=.8));gp=P['glass_pocket'];boolop(face,box('GLASS_POCKET',(gp[0],gp[1]*2,gp[2]),(0,fb,wz),bevel=.6))
boolop(face,cylinder('CAMERA_APERTURE',P['camera_lens_d']+.3,12,(0,fy0,cz),'Y'))
LB=P['lcd_boss_rect'];sy=P['lcd_stack'];lback=fb-gp[1]+sy;P['lcd_back_y']=lback;pcbf=fb-gp[1]+4;P['lcd_pcb_front_y_assumed']=pcbf
for x in (-LB[0]/2,LB[0]/2):
 for z in (wz-LB[1]/2,wz+LB[1]/2):unite(face,cylinder(f'FACE_LCD_BOSS_{x}_{z}',6,pcbf-fb+.2,(x,(fb+pcbf)/2-.1,z),'Y'));hole(face,(x,pcbf,z),2.2,8,'Y')
for x in (-10,26):unite(face,cylinder(f'FACE_PRIV_BOSS_{x}',5,3,(x,fb+1.5-.1,cz),'Y'));hole(face,(x,fb+2,cz),2.0,6,'Y')
part(face,'Ø106黑色面板（LCD窗＋镜头孔＋LCD四柱UNVERIFIED）',motion=True)
lcdf=box('LCD_REAR_CLAMP_FRAME',(LB[0]+8,2,LB[1]+8),(0,lback+1,wz),bevel=2);boolop(lcdf,box('LCD_FRAME_OPEN',(LB[0]-14,6,LB[1]-12),(0,lback+1,wz),bevel=2))
for x in (-LB[0]/2,LB[0]/2):
 for z in (wz-LB[1]/2,wz+LB[1]/2):hole(lcdf,(x,lback+1,z),2.8,6,'Y')
boolop(lcdf,box('LCD_FRAME_HEADER_NOTCH',(8,6,22),(lp_x:=P['lcd_pcb'][0]/2-3,lback+1,wz)))
part(lcdf,'LCD后压框（周边夹持，孔位UNVERIFIED）',motion=True)
cm=P['camera_module'];crs=P['camera_recess'];cy=fb+cm[1]/2+.2+crs
cc=box('CAMERA_CRADLE',(cm[0]+5,cm[1]+1.6+crs,cm[2]+5),(0,fb+(cm[1]+1.6+crs)/2,cz),bevel=.6);boolop(cc,box('CAMERA_POCKET',(cm[0]+1.2,cm[1]+1.4,cm[2]+1.2),(0,cy-.5,cz)));boolop(cc,box('CAMERA_FPC_EXIT',(6,10,8),(0,cy+3,cz-4)))
boolop(cc,cylinder('CAM_CRADLE_LENS_TUBE',P['camera_lens_d'],cm[1]+1.6+crs+2,(0,fb+(cm[1]+1.6+crs)/2,cz),'Y'))
part(cc,'摄像头8×8托架（贴面板背面）',motion=True)
pv=box('PRIVACY_GUIDE',(42,1.6,12),(8,fy0-ft_/2-.8,cz),bevel=.4);boolop(pv,box('PRIV_TRACK',(28,2,8.4),(8,fy0-ft_/2-.4,cz)));boolop(pv,box('PRIV_TAB_SLOT',(14,4,3.2),(5.5,fy0-ft_/2-1,cz)))
for x in (-10,26):hole(pv,(x,fy0,cz),2.4,8,'Y')
part(pv,'隐私滑盖导轨（前贴面板）',motion=True)
bl=box('PRIVACY_BLADE',(10,.8,8),(0,fy0-ft_/2-1.0,cz),bevel=.2);unite(bl,box('PRIV_TAB',(2.4,1.6,2.4),(0,fy0-ft_/2-2.0,cz)))
part(bl,'隐私滑片（打开位置在x=11+）',motion=True)
bw,bt,bh=P['board'];pcy=lback+2.5+P['board_comp']+bt/2+.1;P['board_pcb_y']=pcy;btop=cz+3;bz=btop-bh/2;P['board_z']=(btop-bh,btop)
P['camera_fpc_span_mm']=round(math.hypot((pcy-bt/2)-(cy+cm[1]/2),btop-6-(cz-cm[2]/2)),2);P['camera_fpc_slack_mm']=round(P['camera_fpc']-P['camera_fpc_span_mm'],2);assert P['camera_fpc_span_mm']<=P['camera_fpc_max_span'],P['camera_fpc_span_mm']
cb0=hft+fh;corecr=box('CORE_BOARD_CRADLE',(bw+8,8,5),(0,pcy,cb0+2.5),bevel=.6);boolop(corecr,box('CORE_SLOT',(bw+.6,bt+.2,10),(0,pcy,cb0+7)))
for x in (-bw/2-2.5,bw/2+2.5):
 unite(corecr,box(f'CORE_EDGE_RAIL_{x}',(3,8,btop-bh+20-cb0-.2),(x,pcy,(cb0+.2+btop-bh+20)/2)));boolop(corecr,box(f'CORE_RAIL_SLOT_{x}',(2.2,bt+.2,60),(x-math.copysign(.9,x)*0+(-1 if x>0 else 1)*.5,pcy,hft+38)))
for x in (-10,10):hole(neck,(x,pcy,cb0),2.4,5);hole(corecr,(x,pcy,cb0+2),3.4,10)
part(corecr,'核心板竖直边缘托架（固定于头底）',motion=True)
print('STAGE face/head parts',flush=True)
#@@PROX@@
# ---------- PROXIES (never printed) ----------
lg=P['lcd_glass'];lp_=P['lcd_pcb']
proxy(box('LCD_GLASS_PROXY',(lg[0],lg[1],lg[2]),(0,fb-gp[1]+lg[1]/2+.05,wz)),'LCD glass',True,GLASS)
proxy(box('LCD_MODULE_PROXY',(lg[0],pcbf-(fb-gp[1]+lg[1]+.1),lg[2]),(0,(pcbf+fb-gp[1]+lg[1]+.1)/2,wz)),'LCD glass/backlight (assumed 4 mm to PCB)',True,BLACK)
proxy(box('LCD_PCB_STACK_PROXY',(lp_[0],lback-pcbf-.1,lp_[2]),(0,(pcbf+lback-.1)/2,wz)),'LCD PCB+components 85x50, stack total 11',True)
proxy(box('LCD_HEADER_KEEPOUT',(4,P['dupont_clear'],20),(lp_[0]/2-3,lback+P['dupont_clear']/2+.1,wz)),'LCD 14p dupont clearance',True,CABLE)
proxy(box('CAMERA_MODULE_PROXY',cm,(0,cy,cz)),'camera 8x8x4',True)
proxy(box('CORE_BOARD_PCB',(bw,bt,bh),(0,pcy,bz)),'GOOUU 62.6x28.3',True)
proxy(box('CORE_BOARD_COMPONENTS',(bw-2,P['board_comp'],bh-4),(0,pcy-bt/2-P['board_comp']/2-.05,bz)),'components 6mm',True)
proxy(box('CORE_BOARD_PINS',(bw-4,P['board_pins'],bh-10),(0,pcy+bt/2+P['board_pins']/2+.05,bz-2)),'header pins 8mm',True)
proxy(box('USB_PLUG_ACCESS',(bw-6,10,P['usb_access']),(0,pcy,btop+P['usb_access']/2+.2)),'USB-C debug access',True,CABLE)
proxy(ring('BEARING_LOWER',42,30,7,(0,0,bz0)),'6806',False,METAL);proxy(ring('BEARING_UPPER',42,30,7,(0,0,bz1)),'6806',False,METAL)
sbx=box('SERVO_MG90S',(sb_[1],sb_[0],sb_[2]),(SCX,0,sbz+sb_[2]/2));unite(sbx,box('SERVO_EARS',(P['servo_ear_len'],sb_[0],2.5),(SCX,0,ez0+1.25)));unite(sbx,cylinder('SERVO_SPLINE',5,hz-2-(sbz+sb_[2])+.01,(SX,0,(hz-2+sbz+sb_[2])/2)))
proxy(sbx,'MG90S',False,BLUE)
proxy(cylinder('SPEAKER_40',spd,spl,(0,spy,spz),'Y'),'speaker 40x17',False,BLACK)
for sx in (-1,1):proxy(cylinder(f'INMP441_{sx}',P['mic_d'],1.6,(sx*mx,mwy-2.8,mz),'Y'),'INMP441 Ø14',False)
proxy(box('MAX98357A',(aw,ad,1.6),(ax,ay,af+2.5+.8+.05)),'amp 17.7x19.1',False)
proxy(box('USBC_POWER_IN',PB,(0,pby,pbz)),'USB-C 5V input UNVERIFIED',False)
proxy(box('TACT_SWITCH_6MM',(6,6,4.3),(kx,ky,lit-6.8+2.15)),'tact 6mm',False,BLACK)
# Belt pitch path (fixed set) as visual proxy
r1,r2=D/2,d/2;pts=[]
for i in range(49):t=-math.pi/2+math.pi*i/48;pts.append((r1*math.cos(t),r1*math.sin(t),pz))
for i in range(49):t=math.pi/2+math.pi*i/48;pts.append((SX+r2*math.cos(t),r2*math.sin(t),pz))
cu=bpy.data.curves.new('N6_BELT','CURVE');cu.dimensions='3D';cu.bevel_depth=.6*U;spl_=cu.splines.new('POLY');spl_.points.add(len(pts)-1)
for q,p in zip(spl_.points,pts):q.co=(*[v*U for v in p],1)
spl_.use_cyclic_u=True;bo=bpy.data.objects.new('N6_BELT_PITCH_PROXY',cu);PROX.objects.link(bo);bo.data.materials.append(BLACK)
# Cable keep-out through 22 bore + strain-relief saddles each side
ck=cylinder('CABLE_BORE_KEEPOUT',P['cable_keepout_d'],hft+8-(s0-6),(0,0,(hft+8+s0-6)/2));keepout(ck,True,'~9 wires through 22 bore')
sd1=box('CABLE_SADDLE_BASE',(14,10,5),(-20,0,fl+2.5),bevel=.6);boolop(sd1,box('SADDLE1_SLOT',(14+2,4,3),(-20,0,fl+3.6)));floor_screw_up(sd1,-20,4)
hole(sd1,(-20,4,fl+2),2.6,8)
part(sd1,'线束固定鞍（底座侧）')
sd2=box('CABLE_SADDLE_HEAD',(14,10,5),(hsx,hsy,hft+3+2.5),bevel=.6);boolop(sd2,box('SADDLE2_SLOT',(16,4,3),(hsx,hsy+2,hft+3+3.6)));hole(sd2,(hsx,hsy,hft+5),3.0,8)
part(sd2,'线束固定鞍（头侧）',motion=True)
# ---------- yaw parenting: everything rotating + their control objects ----------
def deps(o,acc):
 for m in o.modifiers:
  for prop in ('object','offset_object'):
   t=getattr(m,prop,None)
   if t and t not in acc:acc.add(t);deps(t,acc)
 return acc
rotobjs={bpy.data.objects[n] for n in rotating}
allrot=set(rotobjs)
for o in rotobjs:deps(o,allrot)
fixedobjs={o for o in scene.objects if o.name not in rotating and o.type=='MESH' and o.users_collection[0] in (PARTS,PROX)}
fixdeps=set()
for o in fixedobjs:deps(o,fixdeps)
shared=(allrot-rotobjs)&fixdeps
if shared:print('WARN shared controls',[o.name for o in shared])
for o in allrot-shared:
 if o.parent is None and o!=yaw:mb=o.matrix_basis.copy();o.parent=yaw;o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=mb
print('STAGE proxies+yaw',flush=True)
#@@SCENE@@
# ---------- world, lights, ortho cameras (v4 style), save ----------
scene.world=bpy.data.worlds.new('N6_NEUTRAL_WORLD');scene.world.use_nodes=True
bg=next(x for x in scene.world.node_tree.nodes if x.type=='BACKGROUND');bg.inputs['Color'].default_value=(.72,.75,.8,1);bg.inputs['Strength'].default_value=.35
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
def point(o,p):o.rotation_euler=(Vector(p)*U-o.location).to_track_quat('-Z','Y').to_euler()
def light(n,loc,power,size,target):
 dd=bpy.data.lights.new('N6_'+n,'AREA');dd.energy=power;dd.shape='DISK';dd.size=size*U;o=bpy.data.objects.new('N6_'+n,dd);PRES.objects.link(o);o.location=Vector(loc)*U;point(o,target)
light('KEY',[-320,-380,500],9,350,[0,0,110]);light('FILL',[260,-80,270],4,260,[0,0,120]);light('REAR',[100,220,330],6,200,[0,0,135])
gm=material('REVIEW_GROUND',(.64,.63,.60),.85);g=box('GROUND',(6000,6000,2),(0,0,-1.0),c=PRES,mat=gm)
cams={}
for n,loc,tg,sc in [('HERO',[330,-600,280],[0,0,112],345),('FRONT',[0,-650,105],[0,0,105],335),('SIDE',[650,0,105],[0,0,105],335),('TOP',[0,0,650],[0,0,100],280),('INTERNAL',[350,-600,340],[0,0,100],300)]:
 cd=bpy.data.cameras.new('N6_'+n);o=bpy.data.objects.new('N6_CAM_'+n,cd);CAMS.objects.link(o);o.location=Vector(loc)*U;point(o,tg);cd.type='ORTHO';cd.ortho_scale=sc*U;cams[n]=o
scene.camera=cams['HERO']
for o in PROX.objects:o.hide_render=o.name not in ('N6_LCD_GLASS_PROXY','N6_CAMERA_MODULE_PROXY')
yaw.rotation_euler.z=0;bpy.context.view_layer.update()
BLEND=ROOT/'EffMeet2_NOMI_布局A_v6_紧凑候选.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND),compress=True)
print('STAGE saved',BLEND,flush=True)
#@@CHECKS@@
# ---------- STAGE 1 CHECKS ----------
def ev(o):
 dg=bpy.context.evaluated_depsgraph_get();e=o.evaluated_get(dg);me=e.to_mesh();bm=bmesh.new();bm.from_mesh(me);bm.transform(e.matrix_world);bm.transform(Matrix.Scale(1/U,4));e.to_mesh_clear();return bm
def bbox(bm):
 if not bm.verts:return None
 return [[round(min(v.co[i] for v in bm.verts),2) for i in range(3)],[round(max(v.co[i] for v in bm.verts),2) for i in range(3)]]
def stats(bm):
 bm.verts.ensure_lookup_table();adj={v.index:set() for v in bm.verts}
 for e_ in bm.edges:a_,b_=[v.index for v in e_.verts];adj[a_].add(b_);adj[b_].add(a_)
 rem=set(adj);n=0
 while rem:
  n+=1;st=[rem.pop()]
  while st:
   for k_ in adj[st.pop()]&rem:rem.remove(k_);st.append(k_)
 return {'faces':len(bm.faces),'nonmanifold_edges':sum(not e_.is_manifold for e_ in bm.edges),'boundary_edges':sum(e_.is_boundary for e_ in bm.edges),'components':n,'volume_mm3':round(abs(bm.calc_volume(signed=True)),1),'bbox':bbox(bm)}
pobj=[bpy.data.objects[p['object']] for p in parts];xobj=[o for o in PROX.objects if o.type=='MESH']
def trees():
 T={}
 for o in pobj+xobj:
  bm=ev(o);bi=bm.copy();bi.normal_update()
  for v in bi.verts:v.co-=v.normal*.05
  T[o.name]=(BVHTree.FromBMesh(bi),bbox(bm),bm);bi.free()
 return T
def bb_hit(a,b,t=.01):return a and b and all(a[0][i]<=b[1][i]+t and b[0][i]<=a[1][i]+t for i in range(3))
def overlaps(T,names_a,names_b,same=False):
 out=[]
 for i,a in enumerate(names_a):
  for b in (names_a[i+1:] if same else names_b):
   if a==b or not bb_hit(T[a][1],T[b][1]):continue
   ov=T[a][0].overlap(T[b][0]);n=len(ov)
   if n:
    T[a][2].faces.ensure_lookup_table();c=T[a][2].faces[ov[0][0]].calc_center_median()
    out.append({'a':a[3:],'b':b[3:],'tri_pairs':n,'sample_mm':[round(x,1) for x in c]})
 return out
yaw.rotation_euler.z=0;bpy.context.view_layer.update();T=trees()
R={'stage':'STAGE1_reversible_blockout','manufacturing_ready':False,'hardware_validated':False,'params':{k:v for k,v in P.items()}}
allb=[T[n][1] for n in T if T[n][1]];R['overall_bbox_mm']=[[min(b[0][i] for b in allb) for i in range(3)],[max(b[1][i] for b in allb) for i in range(3)]]
R['part_bbox_mm']={p['id']+' '+p['object'][3:]:T[p['object']][1] for p in parts}
R['shell_stats']={o.name[3:]:stats(T[o.name][2]) for o in (head,face,neck,cup,lid)}
R['part_mesh_issues']={o.name[3:]:{k:v for k,v in stats(T[o.name][2]).items() if k in('nonmanifold_edges','components')} for o in pobj}
pn=[o.name for o in pobj];xn=[o.name for o in xobj]
R['overlap_part_part']=overlaps(T,pn,pn,True);R['overlap_part_proxy']=overlaps(T,pn,xn)
print('STAGE overlaps',len(R['overlap_part_part']),len(R['overlap_part_proxy']),flush=True)
#@@CHECKS2@@
# containment: proxy bbox corners inside base inner profile (fixed) or head outer control (rotating, via ray parity)
fullbm=ev(full);FT=BVHTree.FromBMesh(fullbm)
def inside_head(p):
 hits=0;o=Vector(p);dr=Vector((0.0123,0.0071,1))
 while True:
  r=FT.ray_cast(o,dr)
  if r[0] is None:break
  hits+=1;o=r[0]+dr*1e-3
 return hits%2==1
cont=[]
for o in xobj:
 b=T[o.name][1];pts=[(x,y,z) for x in (b[0][0],b[1][0]) for y in (b[0][1],b[1][1]) for z in (b[0][2],b[1][2])]
 if o.name in rotating:ok=all(inside_head(p) and p[2]>=hft-.01 for p in pts);where='head'
 else:ok=all(fl-.01<=z<=lit+.01 and x*x+(y/P['base_y_scale'])**2<=base_inner_r(min(max(z,fl+.01),lit))**2+1 for x,y,z in pts);where='base'
 cont.append({'proxy':o.name[3:],'shell':where,'inside':ok})
R['proxy_containment']=cont
rn=[n for n in pn+xn if n in rotating];fn=[n for n in pn+xn if n not in rotating]
R['yaw']=[]
for deg in (-45,0,45):
 yaw.rotation_euler.z=math.radians(deg);bpy.context.view_layer.update();TT=trees()
 R['yaw'].append({'deg':deg,'rot_vs_fixed':overlaps(TT,rn,fn)})
 for v in TT.values():v[2].free()
yaw.rotation_euler.z=0;bpy.context.view_layer.update()
R['belt']={'pitch_D':round(D,3),'pitch_d':round(d,3),'table':belts,'picked':pick,'L_check':round(Lchk,3),'C_min_clearance':Cmin,'ratio':P['driven_T']/P['driver_T'],'servo_pm90_to_head_deg':90*P['driver_T']/P['driven_T'],'head_hard_stop_deg':P['stop_contact'],'servo_deg_at_hard_stop':P['stop_contact']*2,'servo_deg_at_soft_stop':P['stop_soft']*2}
(PROD/'stage1-checks.json').write_text(json.dumps(R,ensure_ascii=False,indent=1,default=str),encoding='utf8')
print('SUMMARY overall',R['overall_bbox_mm']);print('SUMMARY shells',json.dumps(R['shell_stats']))
print('SUMMARY pp',json.dumps(R['overlap_part_part']));print('SUMMARY px',json.dumps(R['overlap_part_proxy']))
print('SUMMARY cont',[c['proxy'] for c in cont if not c['inside']]);print('SUMMARY yaw',json.dumps([(y['deg'],len(y['rot_vs_fixed'])) for y in R['yaw']]),json.dumps(R['yaw'][0]['rot_vs_fixed']))
print('SUMMARY belt',json.dumps(R['belt']));print('SUMMARY partissues',{k:v for k,v in R['part_mesh_issues'].items() if v['nonmanifold_edges'] or v['components']!=1})
R['overlap_method']='BVH overlap of evaluated meshes inset 0.05 mm along vertex normals (touching faces not counted)'
(PROD/'stage1-checks.json').write_text(json.dumps(R,ensure_ascii=False,indent=1,default=str),encoding='utf8')
if os.environ.get('EFFMEET_SKIP_RENDER')!='1':
 def render(fn,cam):scene.camera=cams[cam];scene.render.filepath=str(REN/fn);bpy.ops.render.render(write_still=True);print('RENDERED',fn,flush=True)
 render('01_hero.png','HERO');render('02_front.png','FRONT');render('03_side.png','SIDE');render('04_top.png','TOP')
 for o in (cup,lid,head,face):o.hide_render=True
 for o in PROX.objects:o.hide_render=False
 render('05_internal.png','INTERNAL')
 for o in (cup,lid,head,face):o.hide_render=False
 for o in PROX.objects:o.hide_render=o.name not in ('N6_LCD_GLASS_PROXY','N6_CAMERA_MODULE_PROXY')
 scene.camera=cams['HERO']
(PROD/'parts-seed.json').write_text(json.dumps({'scene':scene.name,'parts':parts},ensure_ascii=False,indent=1),encoding='utf8')
print('V6_DONE',flush=True)
