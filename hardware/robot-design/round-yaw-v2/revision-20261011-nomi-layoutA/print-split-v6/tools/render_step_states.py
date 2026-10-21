# -*- coding: utf-8 -*-
"""Batch-render per-step assembly state images for ASSEMBLY-图解版.md.

Opens the v6 blend (never saves it), loops steps 04-32 in ONE blender session:
  - toggles hide_render per the step's object set
  - creates runtime-only proxies (TMP_SCREW x4, TMP_WIRE) — not written back
  - sets object colors (workbench OBJECT shading): printed grey 0.75,
    electronics proxies dark/blue-grey by name class
  - workbench engine, studio light, cavity BOTH, film transparent, 720x720 PNG
Output: print-split-v6/steps_img/step-NN.png
Run: blender -b --python tools/render_step_states.py
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

V6 = r"D:\_wb_tmp\effmeet2_scan\EffMeet2\hardware\robot-design\round-yaw-v2\revision-20261011-nomi-layoutA\print-split-v6"
BLEND = os.path.join(V6, "EffMeet2_NOMI_布局A_v6_紧凑候选.blend")
OUT = os.path.join(V6, "steps_img")
os.makedirs(OUT, exist_ok=True)

# ---------- part id -> scene object name ----------
P = {
 'P01':'N6_BASE_CUP', 'P02':'N6_BASE_LID', 'P03':'N6_DRIVEN_64T', 'P04':'N6_DRIVER_32T',
 'P05':'N6_BEARING_TOWER_LOWER_SEAT', 'P06':'N6_UPPER_BEARING_SEAT',
 'P07':'N6_STACK_SPACER_0', 'P08':'N6_STACK_SPACER_1', 'P09':'N6_STACK_SPACER_2', 'P10':'N6_STACK_SPACER_3',
 'P11':'N6_HOLLOW_LOAD_SHAFT', 'P12':'N6_SHAFT_LOWER_LOCK_COLLAR', 'P13':'N6_YAW_STOP_ARM',
 'P14':'N6_SHORT_YAW_NECK', 'P15':'N6_SERVO_ADJUSTABLE_CRADLE', 'P16':'N6_SPEAKER_CRADLE',
 'P17':'N6_AMP_LOW_TRAY', 'P18':'N6_POWER_IN_TRAY',  # P18T 无场景对象（仅在3MF），不渲染
 'P19':'N6_STOP_KEY_CAP', 'P20':'N6_TACTILE_HOLDER',
 'P21':'N6_MIC_RETAINER_-1', 'P22':'N6_MIC_RETAINER_1',  # 已作废件，默认不显示
 'P23':'N6_HEAD_SHELL', 'P24':'N6_FACE_PANEL', 'P25':'N6_LCD_REAR_CLAMP_FRAME',
 'P26':'N6_CAMERA_CRADLE', 'P27':'N6_PRIVACY_GUIDE', 'P28':'N6_PRIVACY_BLADE',
 'P29':'N6_CORE_BOARD_CRADLE', 'P30':'N6_CABLE_SADDLE_BASE', 'P31':'N6_CABLE_SADDLE_HEAD',
 'P33':'N6_CAMERA_BACK_PLATE',  # P32 无场景对象（仅在3MF），不渲染
}
MIC = ['N6_INMP441_-1', 'N6_INMP441_1']
AMP = ['N6_MAX98357A']
SPK = ['N6_SPEAKER_40']
SERVO = ['N6_SERVO_MG90S', 'N6_SERVO_WIRE_STUB']
SW = ['N6_TACT_SWITCH_6MM']
BEARL, BEARU = 'N6_BEARING_LOWER', 'N6_BEARING_UPPER'
LCD = ['N6_LCD_GLASS_PROXY','N6_LCD_MODULE_PROXY','N6_LCD_PCB_STACK_PROXY','N6_LCD_HEADER_KEEPOUT']
CAMM = ['N6_CAMERA_MODULE_PROXY']
CORE = ['N6_CORE_BOARD_PCB','N6_CORE_BOARD_COMPONENTS','N6_CORE_BOARD_PINS','N6_USB_PLUG_ACCESS']
BELT = 'N6_BELT_PITCH_PROXY'
SCREWS = ['TMP_SCREW_1','TMP_SCREW_2','TMP_SCREW_3','TMP_SCREW_4']
WIRE = 'TMP_WIRE'

# base electronics bundle (steps 5-9 install; re-shown from 17 on)
ELEC = MIC + AMP + SPK + SERVO + SW

# ---------- open blend ----------
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene = bpy.context.scene
scene.name = 'STEP_RENDER'  # in-memory only; blend file on disk untouched

# ---------- workbench style (copied from tools/render_parts_idphotos.py, color_type=OBJECT for two-tone) ------
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'OBJECT'
sh.show_cavity = True
sh.cavity_type = 'BOTH'
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'

# hide review ground (would pollute transparent renders)
if 'N6_GROUND' in bpy.data.objects:
    bpy.data.objects['N6_GROUND'].hide_render = True

# ---------- runtime proxies ----------
def cyl(name, d, h, loc):
    me = bpy.data.meshes.new(name + '_MESH')
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=d/2, radius2=d/2, depth=h)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.location = Vector(loc)
    o.hide_render = True
    return o

BOLT_XY = [(26,22),(26,-22),(-22,27),(-22,-27)]  # mm, from build_v6 PARAMS bolt_xy
screws = []
for i,(x,y) in enumerate(BOLT_XY, 1):
    # M3x55-60 shank: from P06 ear top (z=60.6) down to cup floor (z=2); units = meters
    screws.append(cyl('TMP_SCREW_%d' % i, 0.003, 0.0586, (x*0.001, y*0.001, 0.0313)))
wire = cyl(WIRE, 0.004, 0.0866, (0, 0, 0.0477))  # through P11 Ø22 bore, floor -> above shaft top

TMP_COLORS = {
 'TMP_SCREW': (0.55, 0.56, 0.58, 1.0),
 'TMP_WIRE':  (0.45, 0.38, 0.30, 1.0),
}
PRINTED_GREY = (0.75, 0.76, 0.78, 1.0)
ELEC_DARK    = (0.28, 0.30, 0.34, 1.0)   # MIC/SPEAKER/AMP/SWITCH/USBC/BELT etc
ELEC_BLUEGY  = (0.30, 0.38, 0.48, 1.0)   # LCD/CAM/CORE/BOARD/GOOUU
ELEC_SERVO   = (0.34, 0.42, 0.55, 1.0)   # SERVO

def classify(o):
    n = o.name.upper()
    if n.startswith('TMP_SCREW'): return TMP_COLORS['TMP_SCREW']
    if n.startswith('TMP_WIRE'):  return TMP_COLORS['TMP_WIRE']
    colls = {c.name for c in o.users_collection}
    if 'N6_COMPONENT_PROXIES' in colls:
        if 'SERVO' in n: return ELEC_SERVO
        if any(k in n for k in ('LCD','CAM','CORE','GOOUU','BOARD')): return ELEC_BLUEGY
        return ELEC_DARK
    return PRINTED_GREY

for o in scene.objects:
    o.color = classify(o)

# ---------- camera ----------
cd = bpy.data.cameras.new('STEP_CAM')
cd.lens = 50
cam = bpy.data.objects.new('STEP_CAM', cd)
scene.collection.objects.link(cam)
scene.camera = cam

def vis_bbox(names):
    pts = []
    for nm in names:
        o = bpy.data.objects.get(nm)
        if o is None or o.hide_render: continue
        mw = o.matrix_world
        for c in o.bound_box:
            pts.append(mw @ Vector(c))
    if not pts: return None
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    return Vector((min(xs),min(ys),min(zs))), Vector((max(xs),max(ys),max(zs)))

def frame(target_names=None, direction=(1,-1,0.62), ortho=False, zoom=1.18, min_radius=0.05):
    """Place cam looking at bbox center from direction; perspective or ortho."""
    if target_names is None:
        vis = [o.name for o in scene.objects if not o.hide_render and o.type in ('MESH','CURVE')]
    else:
        vis = [n for n in target_names if bpy.data.objects.get(n) and not bpy.data.objects[n].hide_render]
    bb = vis_bbox(vis)
    if bb is None:
        bb = (Vector((-0.1,-0.1,0)), Vector((0.1,0.1,0.2)))
    mn, mx = bb
    ctr = (mn+mx)/2
    radius = max((mx-mn).length/2, min_radius)
    d = Vector(direction).normalized()
    cam.rotation_euler = d.to_track_quat('Z','Y').to_euler()  # -Z looks at target => cam 'looks' along -Z; place at ctr+d*dist
    if ortho:
        cd.type = 'ORTHO'
        cam.location = ctr + d * (radius*4+0.3)
        # compute camera-space extents of bbox corners
        bpy.context.view_layer.update()
        mwi = cam.matrix_world.inverted()
        xs=[];ys=[]
        for cx in (mn.x,mx.x):
            for cy in (mn.y,mx.y):
                for cz in (mn.z,mx.z):
                    v = mwi @ Vector((cx,cy,cz)); xs.append(abs(v.x)); ys.append(abs(v.y))
        cd.ortho_scale = 2*max(max(xs),max(ys))*zoom
    else:
        cd.type = 'PERSP'
        fov = cd.angle
        dist = radius / math.sin(fov/2) * zoom
        cam.location = ctr + d * dist
    bpy.context.view_layer.update()
    return ctr, radius

def set_vis(names):
    names = set(names)
    for o in scene.objects:
        if o.type in ('MESH','CURVE') and o.name not in ('STEP_CAM',):
            # never show keepouts / review ground / original cams-lights
            colls = {c.name for c in o.users_collection}
            if 'N6_KEEP_OUTS' in colls or 'N6_REVIEW_ONLY' in colls or 'N6_NATIVE_CONTROLS' in colls:
                o.hide_render = True
                continue
            o.hide_render = o.name not in names

# ---------- step definitions ----------
# each: (step_no, [object names visible], camera_key)
S = P  # alias
def stack14():
    return [S['P01'], S['P05'], BEARL, S['P07'],S['P08'],S['P09'],S['P10'], BEARU, S['P06']] + SCREWS

STEPS = []
STEPS.append((4,  [S['P01'], S['P02']], 'default'))
STEPS.append((5,  [S['P01']] + MIC, 'cup'))
STEPS.append((6,  [S['P01']] + MIC + [S['P17']] + AMP, 'cup'))
STEPS.append((7,  [S['P01']] + MIC + [S['P17'], S['P16']] + AMP + SPK, 'cup'))
STEPS.append((8,  [S['P01']] + MIC + [S['P17'], S['P16'], S['P15']] + AMP + SPK + SERVO, 'cup'))
STEPS.append((9,  [S['P01']] + MIC + [S['P17'], S['P16'], S['P15'], S['P20']] + AMP + SPK + SERVO + SW, 'cup'))
# step 10 (P18T) skipped — object not in blend
STEPS.append((11, [S['P01'], S['P05'], S['P06'], S['P07'],S['P08'],S['P09'],S['P10']] + SCREWS, 'side'))
STEPS.append((12, [S['P01'], S['P05'], BEARL], 'top'))
STEPS.append((13, [S['P01'], S['P05'], BEARL, S['P07'],S['P08'],S['P09'],S['P10']], 'default'))
STEPS.append((14, stack14(), 'top'))
STEPS.append((15, stack14() + [S['P11']], 'default'))
STEPS.append((16, stack14() + [S['P11'], S['P12']], 'default'))
STEPS.append((17, stack14() + [S['P11'], S['P12'], S['P03'], S['P04']] + ELEC, 'default'))
STEPS.append((18, stack14() + [S['P11'], S['P12'], S['P03'], S['P04'], S['P13']] + ELEC, 'default'))
base19 = stack14() + [S['P11'], S['P12'], S['P03'], S['P04'], S['P13']] + ELEC
STEPS.append((19, base19 + [BELT], 'default'))
STEPS.append((20, base19 + [BELT, WIRE], 'default'))
STEPS.append((21, base19 + [BELT, WIRE, S['P02']], 'default'))
STEPS.append((22, base19 + [BELT, WIRE, S['P02'], S['P14']], 'default'))
base22 = base19 + [BELT, WIRE, S['P02'], S['P14']]
STEPS.append((23, base22 + [S['P29']] + CORE, 'head34'))
STEPS.append((24, base22 + [S['P29'], S['P25']] + CORE + LCD, 'headfront'))
STEPS.append((25, base22 + [S['P29'], S['P25'], S['P26'], S['P33']] + CORE + LCD + CAMM, 'headfront'))
STEPS.append((26, base22 + [S['P29'], S['P25'], S['P26'], S['P33']] + CORE + LCD + CAMM, 'head34'))  # 前脸整组检查
STEPS.append((27, base22 + [S['P29'], S['P25'], S['P26'], S['P33'], S['P27'], S['P28']] + CORE + LCD + CAMM, 'headfront'))
STEPS.append((28, base22 + [S['P29'], S['P25'], S['P26'], S['P33'], S['P27'], S['P28'], S['P19']] + CORE + LCD + CAMM, 'default'))
head_in = [S['P29'], S['P25'], S['P26'], S['P33'], S['P27'], S['P28']] + CORE + LCD + CAMM
base28 = base22 + head_in + [S['P19']]
STEPS.append((29, base28 + [S['P23'], S['P24']], 'head34'))   # 头壳+前脸出现=合体
STEPS.append((30, base28 + [S['P23'], S['P24']], 'headfront')) # 前脸压入最终外观
STEPS.append((31, base28 + [S['P23'], S['P24'], S['P30'], S['P31']], 'saddle'))  # 渲染时对 P23/P02 做剖视
STEPS.append((32, base28 + [S['P23'], S['P24'], S['P30'], S['P31']], 'default32'))

HEAD_PARTS_23_28 = [S['P29'], S['P25'], S['P26'], S['P33'], S['P27'], S['P28']] + CORE + LCD + CAMM
HEAD_PARTS_29_30 = HEAD_PARTS_23_28 + [S['P23'], S['P24']]
SADDLE_SET = [S['P30'], S['P31'], WIRE, S['P14'], S['P11']]

yaw = bpy.data.objects.get('N6_YAW_LAYOUT_ANCHOR')

def place_camera(key, step_no):
    if key == 'default':
        frame(None, (1,-1,0.85))
    elif key == 'cup':        # 底座电子步骤：更高俯角看清杯内
        frame(None, (0.45,-0.62,1.45))
    elif key == 'side':       # 正侧视，看干装总高
        frame(None, (1,0.0,0.14), ortho=True, zoom=1.12)
    elif key == 'top':        # 俯视塔内
        tgt = [S['P01'], S['P05'], BEARL, BEARU, S['P06'], S['P07'],S['P08'],S['P09'],S['P10']] + SCREWS
        ctr, _ = frame(tgt, (0.10,-0.32,1.0), ortho=True, zoom=1.15)
        # re-aim ortho at tower center height for better into-cup framing
        cam.location = Vector((0.015,-0.05,0.22))
        cam.rotation_euler = Vector((0.10,-0.32,1.0)).normalized().to_track_quat('Z','Y').to_euler()
        cd.ortho_scale = 0.135
    elif key == 'headfront':  # 前脸正视
        frame(HEAD_PARTS_23_28 if step_no <= 28 else HEAD_PARTS_29_30, (0.03,-1,0.06))
    elif key == 'head34':     # 前 3/4
        frame(HEAD_PARTS_23_28 if step_no <= 28 else HEAD_PARTS_29_30, (0.55,-1,0.28))
    elif key == 'saddle':     # 线鞍特写（渲染循环里对 P23/P02 做剖视隐藏）
        frame(SADDLE_SET, (0.30,0.35,1.25), zoom=1.22)
    elif key == 'default32':  # 整机 3/4，头已偏转
        frame(None, (1,-1,0.55))
    else:
        frame(None, (1,-1,0.62))

# ---------- render loop ----------
print('RENDER_START steps:', [s[0] for s in STEPS], flush=True)
done, skipped = [], []
for step_no, names, camkey in STEPS:
    if yaw: yaw.rotation_euler.z = 0.0
    if step_no == 32 and yaw:
        yaw.rotation_euler.z = math.radians(25.0)  # 头偏转 +25°
    bpy.context.view_layer.update()
    set_vis(names)
    if step_no == 31:
        # 剖视：隐藏头壳与上盖，露出 P30/P31 线鞍与走线路径（其余对象照常显示）
        for hide_nm in (S['P23'], S['P02']):
            o = bpy.data.objects.get(hide_nm)
            if o: o.hide_render = True
    place_camera(camkey, step_no)
    fn = os.path.join(OUT, 'step-%02d.png' % step_no)
    scene.render.filepath = fn
    bpy.ops.render.render(write_still=True)
    ok = os.path.exists(fn) and os.path.getsize(fn) > 1000
    print('SHOT step-%02d %s %s objs=%d' % (step_no, 'OK' if ok else 'EMPTY!', camkey, len(names)), flush=True)
    done.append(step_no)

# step 10 intentionally skipped (P18T not modeled in blend)
skipped.append(10)
print('RENDER_DONE', len(done), 'images ->', OUT, 'skipped:', skipped, flush=True)
