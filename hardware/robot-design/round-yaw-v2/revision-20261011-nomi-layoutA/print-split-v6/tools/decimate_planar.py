import bpy, os, math
CSTL=r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6\candidate-stl"
OUT=r"C:\Users\94823\.qwenworkcn\workspace\mv8u5q649860hdr0\v6rebuild\new-stl"
JOBS={"P02":os.path.join(CSTL,"P02_BASE_LID_UNVERIFIED.stl"),
      "P04":os.path.join(CSTL,"P04_DRIVER_32T_UNVERIFIED.stl")}
for pid,path in JOBS.items():
    bpy.ops.wm.stl_import(filepath=path)
    obj=bpy.context.selected_objects[0]
    n0=len(obj.data.polygons)
    m=obj.modifiers.new("planar",'DECIMATE'); m.decimate_type='DISSOLVE'; m.angle_limit=math.radians(5); m.delimit={'NORMAL','UV','SEAM','SHARP'}
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=m.name)
    n1=len(obj.data.polygons)
    dst=os.path.join(OUT,f"{pid}_decimated.stl")
    bpy.ops.wm.stl_export(filepath=dst, export_selected_objects=True)
    bpy.data.objects.remove(obj,do_unlink=True)
    print(f"{pid}: {n0} -> {n1} polys, exported {dst}")
print("DECIMATE_DONE")
