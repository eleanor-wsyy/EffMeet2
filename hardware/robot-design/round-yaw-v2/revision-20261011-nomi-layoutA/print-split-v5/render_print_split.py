"""Candidate render evidence only. Never save edited presentation state to native source."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parent;REN=ROOT/'renders';REN.mkdir(exist_ok=True);s=bpy.data.scenes['N5_PRINT_SPLIT_CANDIDATE'];bpy.context.window.scene=s;s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=1050;s.render.resolution_percentage=100
for o in s.objects:
 if 'COMPONENT_PROXIES' in str([c.name for c in o.users_collection]):o.hide_render=o.name not in ('N5_LCD_GLASS_PROXY','N5_CAMERA_LENS_PROXY','N5_PURCHASED_SILICONE_FOOT')
def render(name,cam):s.camera=bpy.data.objects['N5_CAM_'+cam];s.render.filepath=str(REN/name);bpy.ops.render.render(write_still=True)
for name,cam in [('01_hero_candidate.png','HERO'),('02_front_candidate.png','FRONT'),('03_side_candidate.png','SIDE'),('04_top_candidate.png','TOP')]:render(name,cam)
yaw=bpy.data.objects['N5_YAW_LAYOUT_ANCHOR']
for deg,name in [(-45,'08_yaw_left_candidate.png'),(45,'09_yaw_right_candidate.png')]:
 yaw.rotation_euler.z=math.radians(deg);bpy.context.view_layer.update();render(name,'HERO')
yaw.rotation_euler.z=0;bpy.context.view_layer.update()
for n in ('HEAD_SHELL','FACE_PANEL','BASE_LID','BASE_CUP'):bpy.data.objects['N5_'+n].hide_render=True
for o in s.objects:
 if 'COMPONENT_PROXIES' in str([c.name for c in o.users_collection]):o.hide_render=False
render('05_internal_candidate.png','INTERNAL')
for n in ('HEAD_SHELL','FACE_PANEL','BASE_LID','BASE_CUP'):bpy.data.objects['N5_'+n].hide_render=False
# New scene of evaluated display copies: motion-independent exploded geometry.
parts=json.loads((ROOT/'parts.json').read_text(encoding='utf8'))['parts'];dg=bpy.context.evaluated_depsgraph_get();meshes=[]
for r in parts:
 o=bpy.data.objects[r['object']];e=o.evaluated_get(dg);me=bpy.data.meshes.new_from_object(e);me.transform(e.matrix_world);meshes.append((r,me))
a=bpy.data.scenes.new('N5_PART_INDEX_REVIEW');bpy.context.window.scene=a;a.world=s.world.copy();a.render.engine='CYCLES';a.cycles.samples=12;a.cycles.use_denoising=True;a.render.resolution_x=2100;a.render.resolution_y=1750;a.render.resolution_percentage=100;a.view_settings.view_transform='AgX';grey=bpy.data.materials['N4_PLA_GREY_PREVIEW']
centers={}
for i,(r,me) in enumerate(meshes):
 o=bpy.data.objects.new('INDEX_'+r['id'],me);a.collection.objects.link(o);mins=Vector([min(v.co[k] for v in me.vertices) for k in range(3)]);maxs=Vector([max(v.co[k] for v in me.vertices) for k in range(3)]);sc=.055/max(maxs-mins);me.transform(Matrix.Translation(-(maxs+mins)/2));me.transform(Matrix.Scale(sc,4));me.materials.clear();me.materials.append(grey);o.location=((i%7-3)*.080,(5-i//7)*.074,.03);centers[r['id']]=Vector(o.location)+Vector((0,-.035,0))
# Neutral physical lights copied, presentation grid is NOT a print plate.
for name in ('KEY','FILL','REAR'):
 original=bpy.data.objects['N5_'+name];o=original.copy();o.data=original.data.copy();a.collection.objects.link(o);o.location*=2.5;o.data.energy*=6;o.data.size*=2.5
camdata=bpy.data.cameras.new('PARTS_INDEX_CAMERA');cam=bpy.data.objects.new('PARTS_INDEX_CAMERA',camdata);a.collection.objects.link(cam);cam.location=(0,-.50,.95);target=Vector((0,.19,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.65;a.camera=cam
bpy.context.view_layer.update();labels={pid:[float(v) for v in world_to_camera_view(a,cam,c)] for pid,c in centers.items()};(ROOT/'production/part-index-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8');a.render.filepath=str(REN/'06_parts_index_raw.png');bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',flush=True)
