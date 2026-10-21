"""Render site-ready stills from the current v6 enclosure model.

Run with Blender:
  blender -b <v6.blend> --python scripts/render_site_assets.py -- <out_dir> [preset]

Presets: test, hero, detail, internal, all
"""
import sys
from pathlib import Path

import bpy


def env_argv():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def set_world_warm():
    world = bpy.context.scene.world
    if not world:
        return
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.968, 0.964, 0.949, 1.0)
    bg.inputs["Strength"].default_value = 0.65


def hide_ground():
    for obj in bpy.data.objects:
        if obj.name in {"N6_GROUND", "GROUND"}:
            obj.hide_render = True


def show_only_robot():
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name.startswith("N6_"):
            if "PROXY" in obj.name and obj.name not in {"N6_LCD_GLASS_PROXY", "N6_CAMERA_MODULE_PROXY"}:
                obj.hide_render = True


def set_camera(name):
    cam = bpy.data.objects.get(f"N6_CAM_{name}")
    if not cam:
        raise SystemExit(f"camera N6_CAM_{name} not found")
    bpy.context.scene.camera = cam


def configure(width, height, samples, transparent):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = transparent
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"


def render(out: Path, filename: str):
    scene = bpy.context.scene
    scene.render.filepath = str(out / filename)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", filename, flush=True)


def main():
    args = env_argv()
    out = Path(args[0]) if args else Path("site/assets/img")
    preset = args[1] if len(args) > 1 else "test"
    out.mkdir(parents=True, exist_ok=True)

    hide_ground()
    show_only_robot()
    set_world_warm()

    if preset == "test":
        configure(600, 720, 8, True)
        set_camera("HERO")
        render(out, "_blender_test.png")
        return

    if preset in {"hero", "all"}:
        configure(2400, 3000, 48, True)
        set_camera("HERO")
        bpy.context.scene.camera.data.ortho_scale *= 0.82
        render(out, "hero.png")

    if preset in {"detail", "all"}:
        configure(2200, 2000, 40, True)
        for cam, name in (("FRONT", "front.png"), ("SIDE", "side.png"), ("TOP", "top.png")):
            set_camera(cam)
            render(out, name)

    if preset in {"internal", "all"}:
        for obj in bpy.data.objects:
            if obj.name.startswith("N6_"):
                obj.hide_render = False
        configure(2200, 1800, 40, True)
        set_camera("INTERNAL")
        render(out, "internal.png")


main()
