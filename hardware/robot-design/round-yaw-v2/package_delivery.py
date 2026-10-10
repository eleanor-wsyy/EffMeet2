"""Build an optional local delivery ZIP without staging duplicate binaries in Git."""
from pathlib import Path
import zipfile,json
ROOT=Path(__file__).resolve().parent
DESIGN=ROOT.parent
out=ROOT/'local-only';out.mkdir(exist_ok=True)
archive=out/'EffMeet2_圆润转头版_建模与硬件清单_v2.zip'
items=[DESIGN/'README.md',DESIGN/'HANDOFF.md',DESIGN/'manifest.json']
items += [ROOT/n for n in ['EffMeet2_圆润转头版_封装布局_v2.blend','BOM.md','PRINT_PLAN.md','README.md','parameters.json','fit-report.json','yaw-clearance.json','build_round_yaw.py','audit_yaw_dependencies.py','EffMeet2_圆润转头版_三姿态预览_修订.png']]
items += list((ROOT/'renders'/'review-02').glob('*.png'))
items += [ROOT/'production'/n for n in ['evaluated_mesh_validation.json','yaw-dependency-audit.json','validation_report.json','construction_graph.json','stage_state.json','native-component-evidence.json']]
items += [ROOT/'concept'/n for n in ['EffMeet2_圆润转头版_主视觉.png','prompt.txt','SOURCE.md']]
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in items:
        assert f.is_file(),str(f)
        z.write(f,str(f.relative_to(DESIGN)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    print(json.dumps({'zip':str(archive),'entries':len(z.namelist()),'bytes':archive.stat().st_size},ensure_ascii=False))
