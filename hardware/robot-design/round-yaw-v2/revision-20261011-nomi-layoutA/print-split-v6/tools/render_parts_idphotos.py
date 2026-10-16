import bpy, os, math
from mathutils import Vector
V6=r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
CS=os.path.join(V6,"candidate-stl"); PM=os.path.join(V6,"plates-merged")
NS=r"C:\Users\94823\.qwenworkcn\workspace\mv8u5q649860hdr0\v6rebuild\new-stl"
OUT=os.path.join(V6,"parts_img"); os.makedirs(OUT,exist_ok=True)
PATHS={
"P01":os.path.join(PM,"P01_v6r3_tolerant_usbc.stl"),"P02":os.path.join(CS,"P02_BASE_LID_UNVERIFIED.stl"),
"P03":os.path.join(CS,"P03_DRIVEN_64T_UNVERIFIED.stl"),"P04":os.path.join(CS,"P04_DRIVER_32T_UNVERIFIED.stl"),
"P05":os.path.join(CS,"P05_BEARING_TOWER_LOWER_SEAT_UNVERIFIED.stl"),"P06":os.path.join(CS,"P06_UPPER_BEARING_SEAT_UNVERIFIED.stl"),
"P07":os.path.join(CS,"P07_STACK_SPACER_0_UNVERIFIED.stl"),"P08":os.path.join(CS,"P08_STACK_SPACER_1_UNVERIFIED.stl"),
"P09":os.path.join(CS,"P09_STACK_SPACER_2_UNVERIFIED.stl"),"P10":os.path.join(CS,"P10_STACK_SPACER_3_UNVERIFIED.stl"),
"P11":os.path.join(CS,"P11_HOLLOW_LOAD_SHAFT_UNVERIFIED.stl"),"P12":os.path.join(CS,"P12_SHAFT_LOWER_LOCK_COLLAR_UNVERIFIED.stl"),
"P13":os.path.join(CS,"P13_YAW_STOP_ARM_UNVERIFIED.stl"),"P14":os.path.join(CS,"P14_SHORT_YAW_NECK_UNVERIFIED.stl"),
"P15":os.path.join(CS,"P15_SERVO_ADJUSTABLE_CRADLE_UNVERIFIED.stl"),"P16":os.path.join(CS,"P16_SPEAKER_CRADLE_UNVERIFIED.stl"),
"P17":os.path.join(CS,"P17_AMP_LOW_TRAY_UNVERIFIED.stl"),"P18":os.path.join(PM,"..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..",""),
}
# fix P18/P32/simple ones explicitly
PATHS["P18T"]=os.path.join(PM,"..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","..","......")
PATHS["P18T"]=os.path.join(NS,"..","..","outputs","print-ready","x.stl")  # placeholder replaced below
PATHS["P18T"]=r"C:\Users\94823\.qwenworkcn\workspace\mv8u5q649860hdr0\v6rebuild\new-stl\P32_MIC_HOLDER_GLUE.stl"  # temp; real P18T from 3mf not needed for ID (use P32 slot)
PATHS.pop("P18",None)
PATHS["P19"]=os.path.join(CS,"P19_STOP_KEY_CAP_UNVERIFIED.stl");PATHS["P20"]=os.path.join(CS,"P20_TACTILE_HOLDER_UNVERIFIED.stl")
PATHS["P21"]=os.path.join(CS,"P21_MIC_RETAINER_-1_UNVERIFIED.stl");PATHS["P22"]=os.path.join(CS,"P22_MIC_RETAINER_1_UNVERIFIED.stl")
PATHS["P23"]=os.path.join(PM,"P23_v6r2_77x45.stl");PATHS["P24"]=os.path.join(PM,"P24_v6r2_77x45.stl");PATHS["P25"]=os.path.join(PM,"P25_v6r2_77x45.stl")
PATHS["P26"]=os.path.join(CS,"P26_CAMERA_CRADLE_UNVERIFIED.stl");PATHS["P27"]=os.path.join(CS,"P27_PRIVACY_GUIDE_UNVERIFIED.stl")
PATHS["P28"]=os.path.join(CS,"P28_PRIVACY_BLADE_UNVERIFIED.stl");PATHS["P29"]=os.path.join(CS,"P29_CORE_BOARD_CRADLE_UNVERIFIED.stl")
PATHS["P30"]=os.path.join(CS,"P30_CABLE_SADDLE_BASE_UNVERIFIED.stl");PATHS["P31"]=os.path.join(CS,"P31_CABLE_SADDLE_HEAD_UNVERIFIED.stl")
PATHS["P32"]=os.path.join(NS,"P32_MIC_HOLDER_GLUE.stl")
PATHS.pop("P18T",None); PATHS.pop("P21",None); PATHS.pop("P22",None)  # P21/P22 scrapped, P18 replaced by P18T->render P32 only; add P18T from micholder? use same P32 geometry label
scene=bpy.data.scenes.new("IDSHOTS"); bpy.context.window.scene=scene
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='SINGLE'
scene.display.shading.single_color=(0.75,0.76,0.78)
scene.display.shading.show_cavity=True; scene.display.shading.cavity_type='BOTH'
scene.render.resolution_x=480; scene.render.resolution_y=480; scene.render.film_transparent=True
cam_data=bpy.data.cameras.new("IDCAM"); cam_data.type='ORTHO'
cam=bpy.data.objects.new("IDCAM",cam_data); scene.collection.objects.link(cam); scene.camera=cam
direction=Vector((1,-1,0.75)).normalized()
for pid,path in sorted(PATHS.items()):
    if not os.path.exists(path): print("MISS",pid); continue
    bpy.ops.wm.stl_import(filepath=path)
    obj=bpy.context.selected_objects[0]
    bb=[obj.matrix_world @ Vector(c) for c in obj.bound_box]
    ctr=sum(bb,Vector())/8; maxd=max((b-ctr).length for b in bb)
    obj.location -= ctr
    cam.location=direction*maxd*4; cam.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
    cam_data.ortho_scale=maxd*2.3
    scene.render.filepath=os.path.join(OUT,pid+".png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)
    print("SHOT",pid)
print("RENDER_DONE")
