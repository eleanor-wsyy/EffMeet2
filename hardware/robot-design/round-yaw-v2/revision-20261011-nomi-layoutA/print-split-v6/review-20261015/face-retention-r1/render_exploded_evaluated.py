import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
src=bpy.data.scenes['N6_FACE_RETENTION_R1_CANDIDATE'];bpy.context.window.scene=src;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
s=bpy.data.scenes.new('R1_EXPLODED_EVALUATED_GEOMETRY');s.world=src.world;s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.view_settings.view_transform='AgX';s.render.resolution_x=1600;s.render.resolution_y=1200
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
for d in pref.devices:d.use=d.type!='CPU'
s.cycles.device='GPU'
attached={'N6_FACE_PANEL','N6_LCD_REAR_CLAMP_FRAME','N6_CAMERA_CRADLE','N6_PRIVACY_GUIDE','N6_PRIVACY_BLADE','N6_LCD_GLASS_PROXY','N6_LCD_MODULE_PROXY','N6_LCD_PCB_STACK_PROXY','N6_CAMERA_MODULE_PROXY'}
show=attached|{'N6_CORE_BOARD_PCB','N6_CORE_BOARD_COMPONENTS','N6_CORE_BOARD_PINS'}
for o in list(src.objects):
 if o.type=='LIGHT':
  c=o.copy();c.data=o.data.copy();s.collection.objects.link(c)
 elif o.type in ('MESH','CURVE') and (not o.hide_render or o.name in show):
  if 'KEEP_OUT' in o.name or 'USB_PLUG_ACCESS' in o.name or 'HEADER_KEEPOUT' in o.name:continue
  e=o.evaluated_get(dg);m=bpy.data.meshes.new_from_object(e);m.transform(e.matrix_world);c=bpy.data.objects.new('EXP_'+o.name,m);s.collection.objects.link(c)
  if o.name in attached:c.location.y=-.055
  if o.name.startswith(('R1_M3_CAP_','R1_M3_SHAFT_')):c.location.y=-.075
bpy.context.window.scene=s
cd=bpy.data.cameras.new('R1_EXP_CAMERA');cam=bpy.data.objects.new('R1_EXP_CAMERA',cd);s.collection.objects.link(cam);cam.location=(.235,-.46,.245);cam.rotation_euler=(Vector((0,-.025,.12))-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=.315;s.camera=cam
s.render.filepath=str(ROOT/'renders/03_exploded_evaluated.png');bpy.ops.render.render(write_still=True)
print('EXPLODED_EVALUATED_DONE',flush=True)
