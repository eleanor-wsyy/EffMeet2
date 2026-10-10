import bpy,json,math,importlib.util
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
scene=bpy.data.scenes['EFFMEET2_PACKAGING_V1'];bpy.context.window.scene=scene
# Neutral modeling evidence: flat major planes; denser true bevels avoid shading artifacts.
for o in scene.objects:
    if o.type=='MESH':
        for p in o.data.polygons:p.use_smooth=False
        for m in o.modifiers:
            if m.type=='BEVEL':m.segments=max(m.segments,24);m.harden_normals=False
            if m.type=='WEIGHTED_NORMAL':m.show_viewport=False;m.show_render=False
scene.render.engine='BLENDER_WORKBENCH'
sh=scene.display.shading;sh.light='FLAT';sh.color_type='MATERIAL';sh.show_shadows=False;sh.show_cavity=True;sh.cavity_type='BOTH';sh.background_type='VIEWPORT';sh.background_color=(0.94,0.94,0.94)
scene.world.color=(0.94,0.94,0.94);scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0
scene.render.resolution_x=1200;scene.render.resolution_y=1050
cam=scene.camera;OUT=ROOT/'renders/review-06';OUT.mkdir(parents=True,exist_ok=True)
def render(name,loc,target=[0,0,94],scale=280):
    cam.location=Vector(loc)*.001;cam.rotation_euler=(Vector(target)*.001-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale*.001
    scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True,scene=scene.name)
render('01_assembled.png',[340,-480,285]);render('02_front.png',[0,-600,94]);render('03_side.png',[600,0,94])
hide_names=['HEAD_SHELL','HEAD_BACK','FACE_MASK','BASE_SHELL','BASE_LID','SPEAKER_GRILLE_RESERVATION','MUTE_BUTTON_POSITION','STATUS_WINDOW_POSITION','CAMERA_LENS_POSITION']
objs=[o for o in scene.objects if o.name in hide_names or o.name.startswith(('EXPRESSION_POSITION','SHUTTER_'))]
for o in objs:o.hide_render=True
render('04_cutaway.png',[340,-480,285]);render('05_section_side.png',[600,0,94])
for o in objs:o.hide_render=False
render('06_top.png',[0,-.1,700],[0,0,90],210)
cam.location=Vector([340,-480,285])*.001;cam.rotation_euler=(Vector([0,0,94])*.001-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.28
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'EffMeet2_席位牌_封装布局_v1_审阅.blend'))
print('FINAL_REVIEW_SAVED')
