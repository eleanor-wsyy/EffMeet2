"""EffMeet2 task-owned reversible packaging blockout. Not a print-ready enclosure."""
import bpy, json, math, itertools, importlib.util, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
OUT=ROOT/'renders'/'review-03'; OUT.mkdir(parents=True,exist_ok=True)
S=0.001
# New task scene; do not mutate any scene that may already exist in a live Blender session.
scene=bpy.data.scenes.new('EFFMEET2_PACKAGING_V1')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'; scene.unit_settings.length_unit='MILLIMETERS'
scene.unit_settings.scale_length=1.0
col=bpy.data.collections.new('EFFMEET2_PACKAGING_V1'); scene.collection.children.link(col)
helpers=bpy.data.collections.new('CUTTERS_AND_KEEP_OUTS'); scene.collection.children.link(helpers)
root=bpy.data.objects.new('HEAD_YAW_CONTROL',None); col.objects.link(root);root.location=Vector(P['yaw']['axis'])*S
root['yaw_deg']=0.0; root.id_properties_ui('yaw_deg').update(min=-45,max=45,description='Visual clearance preview only, not verified servo firmware limits')
drv=root.driver_add('rotation_euler',2).driver;var=drv.variables.new();var.name='yaw_deg';var.type='SINGLE_PROP';var.targets[0].id=root;var.targets[0].data_path='["yaw_deg"]';drv.expression='yaw_deg * 0.0174532925199433'
limit=root.constraints.new('LIMIT_ROTATION');limit.use_limit_z=True;limit.min_z=-math.pi/4;limit.max_z=math.pi/4;limit.owner_space='LOCAL'
materials={}
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=0.48
    materials[name]=m;return m
mat('Neutral_shell',(0.72,0.73,0.72));mat('Neutral_dark',(0.07,0.08,0.09));mat('Optical_placeholder',(0.015,0.02,0.025));mat('Mainboard_diagnostic_green',(0.07,0.27,0.15));mat('LCD_diagnostic_blue',(0.07,0.28,0.4));mat('Camera_diagnostic_gold',(0.6,0.35,0.08));mat('Servo_diagnostic_blue',(0.05,0.16,0.3));mat('Speaker_diagnostic_gray',(0.12,0.13,0.14));mat('Control_diagnostic_orange',(0.8,0.22,0.09));mat('Keepout_wire',(0.3,0.35,0.4))
model=[]; cut=[]; reserves=[]; bodymap={}
def move_collection(obj,target):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    target.objects.link(obj)
def finish(obj,name,material,parent=None):
    obj.name=name;move_collection(obj,col);obj.data.materials.append(materials[material]);model.append(obj)
    if parent:obj.parent=parent;obj.matrix_parent_inverse=parent.matrix_world.inverted()
    obj['production_role']='blockout_proxy';obj['not_print_ready']=True
    return obj
def box(name,size,center,radius=0,material='Neutral_shell',parent=None,profile=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)*S);o=bpy.context.object;o.dimensions=Vector(size)*S
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    finish(o,name,material,parent)
    for p in o.data.polygons:p.use_smooth=True
    if radius:
        b=o.modifiers.new('Editable_profile_bevel','BEVEL');b.width=radius*S;b.segments=12
        if profile:
            a=o.data.attributes.new('bevel_weight_edge','FLOAT','EDGE')
            for e in o.data.edges:
                d=o.data.vertices[e.vertices[0]].co-o.data.vertices[e.vertices[1]].co
                axis=2 if profile=='Z' else 1
                a.data[e.index].value=1.0 if abs(d[axis])>sum(abs(d[j]) for j in range(3) if j!=axis) else 0.0
            b.limit_method='WEIGHT'
        b.harden_normals=True
        n=o.modifiers.new('Review_normals','WEIGHTED_NORMAL');n.keep_sharp=True
    return o
def cyl(name,diam,depth,center,material='Neutral_dark',axis='Z',parent=None):
    rot=(math.pi/2,0,0) if axis=='Y' else (0,0,0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=diam*S/2,depth=depth*S,location=Vector(center)*S,rotation=rot)
    o=bpy.context.object;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);finish(o,name,material,parent)
    b=o.modifiers.new('Small_real_edge_bevel','BEVEL');b.width=0.3*S;b.segments=3
    n=o.modifiers.new('Review_normals','WEIGHTED_NORMAL');n.keep_sharp=True
    return o
def cutter(obj):
    move_collection(obj,helpers);obj.hide_render=True;obj.hide_set(True);obj.display_type='WIRE';model.remove(obj);cut.append(obj);return obj
def difference(host,tool,name):
    m=host.modifiers.new(name,'BOOLEAN');m.operation='DIFFERENCE';m.solver='MANIFOLD';m.object=tool
    return m
head=box('HEAD_SHELL',P['head']['size'],P['head']['center'],14,parent=root,profile=True)
head['nominal_wall_mm']=2.4
head_cavity=cutter(box('HEAD_CAVITY',[143.2,110,115.2],[0,15.4,124],11.6,parent=root,profile=True))
difference(head,head_cavity,'Adjustable_head_cavity_open_rear')
face_cut=cutter(box('FACE_OPENING',[114,10,68],[0,-41,135],11,parent=root,profile=True))
difference(head,face_cut,'Adjustable_front_aperture')
back=box('HEAD_BACK',[142.8,2.4,114.8],[0,42.4,124],11.2,parent=root,profile=True)
mask=box('FACE_MASK',[112,2,66],[0,-42.5,135],10,'Optical_placeholder',root,True)
base=box('BASE_SHELL',P['base']['size'],P['base']['center'],10,profile='Z')
base_cavity=cutter(box('BASE_CAVITY',[131.2,113.2,100],[0,0,54.4],7.6,profile='Z'))
difference(base,base_cavity,'Adjustable_base_cavity_open_top')
lid=box('BASE_LID',[131.0,112.8,2.4],[0,0,50.8],7.4,profile='Z')
shaft_cut=cutter(cyl('YAW_APERTURE_CUTTER',54,10,[0,12,51]))
difference(lid,shaft_cut,'Provisional_bearing_aperture')
yaw=cyl('YAW_SUPPORT',52,12,[0,12,58])
yaw['note']='Bearing/support placeholder, not a selected commercial assembly'
foot=box('NONSLIP_FOOT',P['foot']['size'],P['foot']['center'],8,'Neutral_dark',profile='Z')
# Functional positions remain proxies; no final holes or fasteners are claimed.
port_cut=cutter(box('SPEAKER_PORT_CUTTER',[58,10,34],[0,-57,27],6,profile=True))
difference(base,port_cut,'Provisional_speaker_opening')
grille=box('SPEAKER_GRILLE_RESERVATION',[56,1,32],[0,-58.5,27],6,'Speaker_diagnostic_gray',profile=True)
grille['note']='Solid reservation panel; actual perforation and acoustic gasket not yet engineered'
mute=box('MUTE_BUTTON_POSITION',[18,12,4],[0,0,186],3,'Control_diagnostic_orange',root)
status=box('STATUS_WINDOW_POSITION',[9,1,2],[0,-43.7,91],0.8,'Control_diagnostic_orange',root,True)
for x in [-26,-4]:box('EXPRESSION_POSITION_'+str(x),[8,0.7,2],[x,-43.8,137],0.8,'Control_diagnostic_orange',root,True)
# Hardware bodies and conservative editable keep-outs are independent semantic objects.
for c in P['components']:
    parent=root if c['group']=='head' else None
    color={'MAINBOARD':'Mainboard_diagnostic_green','LCD':'LCD_diagnostic_blue','CAMERA':'Camera_diagnostic_gold','SERVO':'Servo_diagnostic_blue','SPEAKER':'Speaker_diagnostic_gray'}[c['id']]
    if c['id']=='SPEAKER':o=cyl(c['id']+'_BODY',40,18,c['center'],color,'Y',parent)
    else:o=box(c['id']+'_BODY',c['body'],c['center'],0.2,color,parent)
    o['dimension_evidence']=c['evidence'];bodymap[c['id']]=o
    k=box(c['id']+'_KEEP_OUT',c['reserve'],c.get('reserve_center',c['center']),0,'Keepout_wire',parent)
    move_collection(k,helpers);model.remove(k);k.hide_render=True;k.hide_set(True);k.display_type='WIRE';k['dimension_evidence']=c['evidence'];reserves.append(k)
# Optical and control elements are conceptual locations, not a camera CAD reconstruction.
cyl('CAMERA_LENS_POSITION',8,3,[47,-44,157],'Optical_placeholder','Y',root)
box('SHUTTER_TRAVEL_RESERVATION',[28,1,12],[39,-44,157],4,'Neutral_dark',root,True)
box('SHUTTER_THUMB_POSITION',[10,2,9],[33,-45.5,157],3,'Control_diagnostic_orange',root,True)
box('LCD_ACTIVE_AREA_ASSUMPTION',[50,1,38],[-15,-32,137],1,'Optical_placeholder',root,True)
# Floor and accountable neutral diagnostic illumination.
floor=box('REVIEW_FLOOR',[2000,2000,2],[0,0,-1],0,'Neutral_shell');model.remove(floor)
world=bpy.data.worlds.new('EFFMEET2_neutral_review');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(0.65,0.67,0.7,1);world.node_tree.nodes['Background'].inputs[1].default_value=0.35;scene.world=world
for name,loc,energy,size in [('KEY',[-300,-400,550],65,450),('FILL',[350,-100,300],30,350),('TOP',[0,250,450],45,300)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size*S;o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=Vector(loc)*S;o.rotation_euler=(Vector([0,0,100])*S-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('Review_camera');cam=bpy.data.objects.new('Review_camera',camdata);col.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.clip_start=.001;camdata.clip_end=10
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.exposure=-2.0;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.render.image_settings.color_mode='RGB'

def pointcamera(location,target,scale):
    cam.location=Vector(location)*S;cam.rotation_euler=(Vector(target)*S-cam.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale*S

def render(name,location,target=[0,0,94],scale=250):
    pointcamera(location,target,scale);scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True,scene=scene.name)
# Analytic checks against the actual rounded-cavity controls, not the attractive image.
def sdf(p,center,size,r,axis):
    ij=[i for i in range(3) if i!=axis]
    q=[abs(p[i]-center[i])-size[i]/2+r for i in ij]
    d2=math.sqrt(sum(max(t,0)**2 for t in q))+min(max(q),0)-r
    cap=abs(p[axis]-center[axis])-size[axis]/2
    return math.sqrt(max(d2,0)**2+max(cap,0)**2)+min(max(d2,cap),0)
fit=[]
for c in P['components']:
    ce=c.get('reserve_center',c['center']);si=c['reserve']
    corners=[[ce[i]+sign[i]*si[i]/2 for i in range(3)] for sign in itertools.product([-1,1],repeat=3)]
    cv=([0,15.4,124],[143.2,110,115.2],11.6,1) if c['group']=='head' else ([0,0,54.4],[131.2,113.2,100],7.6,2)
    clearance=-max(sdf(pt,*cv) for pt in corners)
    fit.append({'id':c['id'],'reserve_mm':si,'reserve_center_mm':ce,'inside_cavity':clearance>=-0.01,'minimum_corner_clearance_mm':round(clearance,3),'confidence':c['confidence']})
pairs=[]
for a,b in itertools.combinations(P['components'],2):
    if a['group']!=b['group']:continue
    ac=a.get('reserve_center',a['center']);bc=b.get('reserve_center',b['center'])
    gaps=[abs(ac[i]-bc[i])-(a['reserve'][i]+b['reserve'][i])/2 for i in range(3)]
    separated=max(gaps)>=0
    pairs.append({'a':a['id'],'b':b['id'],'separated':separated,'axis_gaps_mm':[round(g,3) for g in gaps]})
fit_report={'scope':'Conservative rectangular keep-out / rounded-cavity blockout checks only','units':'mm','all_reserved_volumes_inside':all(x['inside_cavity'] for x in fit),'all_same_compartment_pairs_separated':all(x['separated'] for x in pairs),'fit':fit,'pairs':pairs,'not_verified':P['unverified'],'yaw_preview':{'limits_deg':[-45,45],'rigid_head_to_base_vertical_gap_mm':12,'cables_torque_acoustics_not_verified':True},'manufacturing_ready':False}
(ROOT/'fit-report.json').write_text(json.dumps(fit_report,indent=2,ensure_ascii=False),encoding='utf-8')
if not fit_report['all_reserved_volumes_inside'] or not fit_report['all_same_compartment_pairs_separated']:raise RuntimeError('Packaging reservation check failed; inspect fit-report.json')
# Validate evaluated mesh topology separately from the conservative packing checks.
dg=bpy.context.evaluated_depsgraph_get();mesh_checks=[]
import bmesh
for o in model:
    if o.type!='MESH':continue
    ev=o.evaluated_get(dg);me=ev.to_mesh();bm=bmesh.new();bm.from_mesh(me)
    boundary=sum(e.is_boundary for e in bm.edges);nonman=sum(not e.is_manifold for e in bm.edges);zero=sum(f.calc_area()<1e-14 for f in bm.faces)
    mesh_checks.append({'object':o.name,'vertices':len(me.vertices),'boundary_edges':boundary,'nonmanifold_edges':nonman,'zero_area_faces':zero})
    bm.free();ev.to_mesh_clear()
report={'schema_version':'1.0','scope':'reversible packaging blockout only','overall_status':'PASS' if all(x['nonmanifold_edges']==0 and x['zero_area_faces']==0 for x in mesh_checks) else 'FAIL','checks':mesh_checks,'fit_report':'../fit-report.json','not_evaluated':P['unverified']+['formal topology and final fasteners','manufacturing tolerances'],'production_release':False}
(ROOT/'production'/'validation_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
if report['overall_status']=='FAIL':raise RuntimeError('Evaluated blockout mesh topology failed')
# Save editable blockout before visual review. No STL/STEP/production GLB is exported.
pointcamera([340,-480,285],[0,0,94],250)
for o in model:o.select_set(False)
head.select_set(True);bpy.context.view_layer.objects.active=head
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=.32;area.spaces.active.region_3d.view_location=Vector([0,0,.094]);area.spaces.active.clip_start=.001;area.spaces.active.clip_end=10
scene['readme']='Packaging blockout, millimeter dimensions, uncertain components are conservative keep-outs. Do not print without mechanical completion.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'EffMeet2_席位牌_封装布局_v1_review03.blend'))
render('01_assembled.png',[340,-480,285])
render('02_front.png',[0,-600,94])
render('03_side.png',[600,0,94])
# Cutaway view: remove shells/covers rather than pretend transparency is solid engineering.
cutaway_hide=[head,back,mask,base,lid,grille,mute,status]+[o for o in model if o.name.startswith(('EXPRESSION_POSITION','SHUTTER_','CAMERA_LENS'))]
for o in cutaway_hide:o.hide_render=True
render('04_cutaway.png',[340,-480,285])
render('05_section_side.png',[600,0,94])
for o in cutaway_hide:o.hide_render=False
render('06_top.png',[0,-.1,700],[0,0,90],210)
# Persist assembly as the default; render toggles never become the saved deliverable state.
print('EFFMEET2_PACKAGING_OK '+json.dumps({'blend':str(ROOT/'EffMeet2_席位牌_封装布局_v1_review03.blend'),'fit':fit_report['all_reserved_volumes_inside'],'mesh_status':report['overall_status'],'renders':6}))
