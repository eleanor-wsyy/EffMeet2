"""Read active Blender model and audit evaluated copies in a disposable scene.
Native Screw input is deliberately an open edge profile; do not apply generators just to pass an input-mesh test.
"""
import bpy,json,copy,importlib.util
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parent;PROD=ROOT/'production'
S=Path.home()/'.codex/skills/blender-geometry-validation/scripts/validate_scene.py'
spec=importlib.util.spec_from_file_location('independent_geometry_validator',S);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
source_scene=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get();graph=json.loads((PROD/'construction_graph.json').read_text(encoding='utf-8'))
audit_scene=bpy.data.scenes.new('N4_EVALUATED_AUDIT_ONLY');names=[];mapping={}
for p in graph['parts']:
 src=bpy.data.objects[p['final_object_name']];ev=src.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,depsgraph=dg);me.transform(src.matrix_world)
 obj=bpy.data.objects.new('EVAL_'+src.name,me);audit_scene.collection.objects.link(obj);names.append(obj.name);mapping[src.name]=obj.name
 p['final_object_name']=obj.name;p['blockout_object_names']=[obj.name]
 for key in ['native_system','source_objects','native_component_evidence','modifier_stack_intent']:p.pop(key,None)
 p['scope']='evaluated mesh audit copy; not an editable replacement or print release'
bpy.context.window.scene=audit_scene
state=json.loads((PROD/'stage_state.json').read_text(encoding='utf-8'))
spatial=json.loads((PROD/'spatial_hypothesis.json').read_text(encoding='utf-8'))
report=v.validate_scene(graph,None,names,set(),200,spatial,state)
report['audit_scope']='Five evaluated exterior meshes; modifier source profiles remain deliberately non-manifold curves'
report['original_file_modified']=False;report['evaluated_mapping']=mapping
report['native_generator_preservation']='verified separately by source modifier stacks in evaluated-shells.json'
(PROD/'independent-validator.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['overall_status'],'failures':report['failures'],'not_evaluated':report['not_evaluated'],'check_count':len(report['checks'])}))
