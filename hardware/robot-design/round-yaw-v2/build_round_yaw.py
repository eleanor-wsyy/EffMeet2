import bpy,bmesh,json,math,itertools,hashlib,os
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
OUT=ROOT/'renders'/os.environ.get('EFFMEET_DESIGN_REVIEW_DIR','rebuild-review')
if OUT.exists() and any(OUT.glob('*.png')):raise FileExistsError('Choose a new EFFMEET_DESIGN_REVIEW_DIR; archived evidence must not be overwritten')
OUT.mkdir(parents=True,exist_ok=True)
LOCAL=ROOT/'local-only';LOCAL.mkdir(exist_ok=True)
U=.001
# Read-only snapshot of the pre-existing v1 scene loaded by the command line.
def old_state():
    return {o.name:{'matrix':[list(row) for row in o.matrix_world],'data':o.data.name if o.data else None,'modifiers':[(m.name,m.type) for m in o.modifiers]} for o in bpy.data.objects if not o.name.startswith('R2_')}
before=old_state();(ROOT/'production'/'protected-scene-before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
scene=bpy.data.scenes.new('R2_ROUND_YAW_BLOCKOUT');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS';scene.unit_settings.scale_length=1
modelcol=bpy.data.collections.new('R2_MODEL');scene.collection.children.link(modelcol)
cutcol=bpy.data.collections.new('R2_NATIVE_CONTROLS');scene.collection.children.link(cutcol)
keepcol=bpy.data.collections.new('R2_KEEP_OUTS');scene.collection.children.link(keepcol)
camcol=bpy.data.collections.new('R2_REVIEW_CAMERAS');scene.collection.children.link(camcol)
model=[];headparts=[];proxy=[]
def move(o,col):
    for c in list(o.users_collection):c.objects.unlink(o)
    col.objects.link(o)
def mat(name,c):
    m=bpy.data.materials.new('R2_'+name);m.diffuse_color=(*c,1);return m
white=mat('CLAY',(0.80,.82,.83));black=mat('FACE',(.045,.055,.065));coral=mat('CORAL',(.95,.25,.13));pcb=mat('PCB',(.12,.36,.22));blue=mat('LCD_SERVO',(.16,.30,.55));gold=mat('CAMERA',(.6,.4,.10));gray=mat('BEARING',(.3,.33,.36))
def reg(o,name,material=white,col=modelcol):
    o.name='R2_'+name;move(o,col)
    if material and o.type=='MESH':o.data.materials.append(material)
    if col==modelcol:model.append(o)
    o['stage']='reversible_blockout';return o
def cube(name,size,center,material=white,bevel=0,col=modelcol):
    bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(center)*U);o=reg(bpy.context.object,name,material,col);o.dimensions=Vector(size)*U
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=o.modifiers.new('Semantic edge transition','BEVEL');m.width=bevel*U;m.segments=6
    return o
def sphere(name,size,center,material=white,col=modelcol):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,radius=1,location=Vector(center)*U)
    o=reg(bpy.context.object,name,material,col);o.scale=Vector(size)*U/2;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for f in o.data.polygons:f.use_smooth=True
    return o
def cyl(name,size,center,axis='Z',material=white,col=modelcol):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1,depth=1,location=Vector(center)*U)
    o=reg(bpy.context.object,name,material,col)
    if axis=='Y':o.rotation_euler[0]=math.pi/2;o.scale=Vector([size[0]/2,size[2]/2,size[1]])*U
    else:o.scale=Vector([size[0]/2,size[1]/2,size[2]])*U
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    for f in o.data.polygons:f.use_smooth=len(f.vertices)==4
    return o
def boolean(o,cutter,operation='DIFFERENCE'):
    m=o.modifiers.new(operation+'_'+cutter.name,'BOOLEAN');m.operation=operation;m.solver='MANIFOLD';m.object=cutter
    cutter.hide_render=True;cutter.hide_set(True);cutter.display_type='WIRE'
    return m
# One radial section is the editable source; native Screw owns the complete surface.
def revolve(name,profile,material=white):
    me=bpy.data.meshes.new('R2_'+name+'_RADIAL_PROFILE');me.from_pydata([(r*U,0,z*U) for r,z in profile],[(i,(i+1)%len(profile)) for i in range(len(profile)) if not (profile[i][0]==0 and profile[(i+1)%len(profile)][0]==0)],[]);me.update()
    o=bpy.data.objects.new('R2_'+name,me);modelcol.objects.link(o);model.append(o);o.data.materials.append(material);o.scale.y=164/180
    m=o.modifiers.new('Radial section 360 degrees','SCREW');m.axis='Z';m.angle=2*math.pi;m.steps=128;m.render_steps=128;m.use_merge_vertices=True;m.merge_threshold=.000001;m.use_smooth_shade=True;m.use_normal_calculate=True
    o['source_role']='single editable radial section; Screw owns repetition';o['stage']='reversible_blockout';return o
def arc(cr,cz,r,t0,t1,n=16):return [(cr+r*math.cos(t0+(t1-t0)*i/n),cz+r*math.sin(t0+(t1-t0)*i/n)) for i in range(n+1)]
to=math.asin(4/14);ti=math.asin(4/11.6)
baseprof=[(0,2),(78,2)]+arc(78,14,12,-math.pi/2,0)[1:]+[(90,64)]+arc(76,64,14,0,to)[1:]+arc(76,64,11.6,ti,0)+[(87.6,14)]+arc(78,14,9.6,0,-math.pi/2)[1:]+[(0,4.4)]
base=revolve('BASE_CUP',baseprof)
lidprof=arc(76,64,14,to,math.pi/2)+[(0,78),(0,75.6),(76,75.6)]+arc(76,64,11.6,math.pi/2,ti)[1:]
lid=revolve('BASE_LID',lidprof)
lidhole=cyl('LID_YAW_HOLE',[48,48,50],[0,0,75],col=cutcol);boolean(lid,lidhole)
foot=cyl('SILICONE_FOOT',[156,140,2],[0,0,1],material=black)
neck=cyl('YAW_NECK',[46,46,25],[0,0,85.5],material=gray)
neckhole=cyl('CABLE_BORE',[22,22,40],[0,0,85.5],col=cutcol);boolean(neck,neckhole)
head=sphere('HEAD_SHELL',P['head']['outer_size'],P['head']['center'])
inner=sphere('HEAD_INNER',[145.2,123.2,139.2],[0,0,150],col=cutcol);boolean(head,inner)
trim=cube('HEAD_BOTTOM_TRIM',[500,500,300],[0,0,-58],col=cutcol);boolean(head,trim)
facecut=cube('HEAD_FACE_OPENING',[500,300,500],[0,-185,150],col=cutcol);boolean(head,facecut)
# The black mask is a removable proxy cover; lip/fasteners intentionally await formal design.
mask=cyl('BLACK_FACE_MASK',[123,2,117],[0,-35.9,150],axis='Y',material=black)
for x in [-12.5,12.5]:
    headparts.append(cube('EXPRESSION_'+str(x),[5,1,13],[x,-37.5,148],coral,2.45))
lens=cyl('CAMERA_LENS',[8,3,8],[0,-38,194],axis='Y',material=black)
shutter=cube('SHUTTER_POSITION',[10,2,8],[12,-38.6,194],gray,3)
headparts += [head,mask,lens,shutter,neck,inner,trim,facecut,neckhole]
buttoncut=cube('MUTE_RECESS',[17,11,7],[0,-51,78],col=cutcol,bevel=3);boolean(lid,buttoncut)
button=cube('MUTE_POSITION',[16,10,3],[0,-51,78],coral,2)
status=cube('STATUS_POSITION',[10,1,2],[0,-82.4,57],coral,.8)
grille=cyl('SPEAKER_PORT_POSITION',[48,1,30],[0,-82.7,42],axis='Y',material=gray);grille['note']='port placement proxy, not perforated grille geometry'
for c in P['components']:
    if c['id'] in ['SPEAKER']:
        o=cyl(c['id'],c['body'],c['center'],axis='Y',material=gray)
    elif c['id']=='BEARING':
        o=cyl(c['id'],c['body'],c['center'],material=gray);hole=cyl('BEARING_CABLE_HOLE',[22,22,30],c['center'],col=cutcol);boolean(o,hole)
    else:o=cube(c['id'],c['body'],c['center'],pcb if c['id']=='MAINBOARD' else gold if c['id']=='CAMERA' else blue,.25)
    proxy.append(o);o['confidence']=c['confidence'];o['actual_product_CAD']=False
    if c['group']=='head':headparts.append(o)
    ko=cube('KEEP_OUT_'+c['id'],c['reserve'],c.get('reserve_center',c['center']),None,col=keepcol);ko.display_type='WIRE';ko.hide_render=True;ko['source']=c['confidence']
    if c['group']=='head':headparts.append(ko)
# A semantic pose anchor is valid for blockout. No completed motor/drive rig is claimed.
yaw=bpy.data.objects.new('R2_HEAD_YAW_POSE',None);modelcol.objects.link(yaw);yaw.location=(0,0,0);yaw.empty_display_type='ARROWS';yaw.empty_display_size=.03;yaw['preview_limits_deg']='-45 to +45, not physical verification'
for o in headparts:
    m=o.matrix_world.copy();o.parent=yaw;o.matrix_world=m
scene.frame_start=1;scene.frame_end=91
for fr,deg in [(1,-45),(31,0),(61,45),(91,0)]:yaw.rotation_euler.z=math.radians(deg);yaw.keyframe_insert(data_path='rotation_euler',index=2,frame=fr)
scene.frame_set(31)
# Analytic conservative keepout checks against the actual generating volumes.
def base_inside(pt):
    x,y,z=pt;r=math.hypot(x,y/(164/180))
    if z<4.4 or z>75.6:return False,-min(abs(z-4.4),abs(z-75.6))
    rad=78+math.sqrt(max(0,9.6**2-(z-14)**2)) if z<14 else 76+math.sqrt(max(0,11.6**2-(z-64)**2)) if z>64 else 87.6
    margin=min(rad-r,z-4.4,75.6-z);return margin>=0,margin
def head_inside(pt):
    q=[(pt[i]-[0,0,150][i])/[72.6,61.6,69.6][i] for i in range(3)];v=sum(a*a for a in q)
    margin=(1-math.sqrt(v))*61.6
    margin=min(margin,pt[2]-92,pt[1]+35)
    return margin>=0,margin
fits=[]
for c in P['components']:
    ce=c.get('reserve_center',c['center']);s=c['reserve'];corners=[[ce[i]+sig[i]*s[i]/2 for i in range(3)] for sig in itertools.product([-1,1],repeat=3)]
    results=[(head_inside if c['group']=='head' else base_inside)(pt) for pt in corners]
    fits.append({'id':c['id'],'inside':all(a for a,b in results),'minimum_conservative_margin_mm':round(min(b for a,b in results),3),'reserve':s,'confidence':c['confidence']})
pairs=[]
for a,b in itertools.combinations(P['components'],2):
    if a['group']!=b['group']:continue
    ac=a.get('reserve_center',a['center']);bc=b.get('reserve_center',b['center']);gaps=[abs(ac[i]-bc[i])-(a['reserve'][i]+b['reserve'][i])/2 for i in range(3)]
    pairs.append({'a':a['id'],'b':b['id'],'separated':max(gaps)>=0,'axis_gaps_mm':[round(v,2) for v in gaps]})
fit={'units':'mm','all_inside':all(c['inside'] for c in fits),'all_pairs_separated':all(c['separated'] for c in pairs),'components':fits,'pairs':pairs,'scope':'conservative analytic generating cavity volumes only, not purchased parts or full assembly','not_verified':P['unverified'],'manufacturing_ready':False}
(ROOT/'fit-report.json').write_text(json.dumps(fit,indent=2,ensure_ascii=False),encoding='utf-8')
if not fit['all_inside'] or not fit['all_pairs_separated']:raise RuntimeError('Keepout test failed, see fit-report.json')
# Validate actual evaluated mesh; profile input is deliberately an edge loop, not final geometry.
dg=bpy.context.evaluated_depsgraph_get();checks=[]
for o in model:
    if o.type!='MESH':continue
    ev=o.evaluated_get(dg);me=ev.to_mesh();bm=bmesh.new();bm.from_mesh(me)
    checks.append({'object':o.name,'vertices':len(me.vertices),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces)})
    bm.free();ev.to_mesh_clear()
after=old_state();protected_ok=before==after
report={'scope':'evaluated blockout geometry, analytic keepouts, pre-existing object snapshot','overall_status':'PASS' if protected_ok and all(c['nonmanifold_edges']==0 and c['zero_area_faces']==0 for c in checks) else 'FAIL','mesh_checks':checks,'protected_scene_objects_unchanged':protected_ok,'not_evaluated':P['unverified'],'stage':'blockout','formal_production_release':False}
(ROOT/'production'/'validation_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
if report['overall_status']=='FAIL':raise RuntimeError('Mesh / protection validation failed, inspect report')
# Neutral body review; no hero material/surfacing or production lighting claims.
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.5;scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=False;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.curvature_ridge_factor=1.2;scene.display.shading.curvature_valley_factor=1.0;scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('R2_REVIEW_WORLD');scene.world.color=(.75,.75,.75);scene.view_settings.view_transform='Standard'
bpy.ops.object.camera_add();cam=reg(bpy.context.object,'REVIEW_CAMERA',None,camcol);cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.clip_end=10;scene.camera=cam
cam.data.ortho_scale=.3
views=[]
def render(name,loc,target=[0,0,108],scale=300):
    cam.location=Vector(loc)*U;cam.rotation_euler=(Vector(target)*U-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*U;scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True,scene=scene.name);views.append(str(OUT/name))
render('01_assembled.png',[350,-500,290])
render('02_front.png',[0,-650,108])
render('03_side.png',[650,0,108])
render('04_top.png',[0,-.01,800],[0,0,108],240)
# Cutaway is shell-hidden layout evidence, not an engineered exploded assembly.
hides=[head,mask,base,lid,foot,grille,button,status,lens,shutter]+[o for o in model if 'EXPRESSION_' in o.name]
for o in hides:o.hide_render=True
render('05_internal.png',[350,-500,300])
render('06_internal_side.png',[650,0,108])
for o in hides:o.hide_render=False
for fr,deg,label in [(1,-45,'left'),(31,0,'center'),(61,45,'right')]:
    scene.frame_set(fr);render('07_yaw_'+label+'.png',[0,-650,180])
scene.frame_set(31)
# Quantitative sweep evidence from real evaluated bounds at 5-degree intervals.
poses=[]
for d in range(-45,46,5):
    yaw.rotation_euler.z=math.radians(d);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();ev=head.evaluated_get(dg);me=ev.to_mesh();minz=min((ev.matrix_world@v.co).z for v in me.vertices)/U;ev.to_mesh_clear();poses.append({'yaw_deg':d,'head_min_z_mm':round(minz,4),'stationary_base_top_z_mm':78,'vertical_gap_mm':round(minz-78,4)})
yaw.rotation_euler.z=0;bpy.context.view_layer.update();scene.frame_set(31)
(ROOT/'yaw-clearance.json').write_text(json.dumps({'pose_anchor_only':True,'sample_step_deg':5,'poses':poses,'neck_to_lid_nominal_radial_clearance_mm':1,'minimum_shell_vertical_gap_mm':min(v['vertical_gap_mm'] for v in poses),'excluded':P['unverified']},indent=2,ensure_ascii=False),encoding='utf-8')
render('08_wireframe.png',[350,-500,290]) if False else None
# Save assembled default with a helpful viewport and preserved original scene.
cam.location=Vector([350,-500,290])*U;cam.rotation_euler=(Vector([0,0,108])*U-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.3
for o in scene.objects:o.select_set(False)
head.select_set(True);bpy.context.view_layer.objects.active=head
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=.4;area.spaces.active.region_3d.view_location=Vector([0,0,.11]);area.spaces.active.clip_start=.001;area.spaces.active.clip_end=10
scene['scope']='Round yaw packaging blockout only; frame1=-45,31=0,61=+45. No print/export release.'
bpy.ops.wm.save_as_mainfile(filepath=str(LOCAL/'EffMeet2_圆润转头版_封装布局_v2_rebuild.blend'))
(ROOT/'production'/'native-component-evidence.json').write_text(json.dumps({'screw':{o.name:[{'name':m.name,'type':m.type} for m in o.modifiers] for o in [base,lid]},'boolean_solver':'MANIFOLD','native_screw_RNA_probe':all(hasattr(base.modifiers[0],n) for n in ['steps','use_merge_vertices','use_normal_calculate']),'units':'meters internally, mm source parameters','old_scene_snapshot_equal':protected_ok,'render_views':views},indent=2),encoding='utf-8')
print('R2_DONE '+json.dumps({'mesh_status':report['overall_status'],'keepout_fit':fit['all_inside'],'old_scene_unchanged':protected_ok,'renders':len(views)}))
