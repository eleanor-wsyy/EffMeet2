"""Package current v4 only; local ZIP does not grant manufacturing release."""
from pathlib import Path
import json,zipfile
ROOT=Path(__file__).resolve().parent;DESIGN=ROOT.parent
M=json.loads((DESIGN/'manifest.json').read_text(encoding='utf-8'))
REV=ROOT/'revision-20261011-nomi-layoutA';LOCAL=ROOT/'local-only';LOCAL.mkdir(exist_ok=True)
files={DESIGN/n for n in ['README.md','HANDOFF.md','AGENTS.md','manifest.json','verify_delivery.py']}
files.update(DESIGN/p for p in M['canonical_files'].values())
for p in REV.rglob('*'):
 if not p.is_file() or p.suffix in ['.blend1','.zip']:continue
 if p.name in ['blender_capabilities.json','protected-scene-before.json']:continue
 if 'renders' in p.parts and 'review-05' not in p.parts:continue
 files.add(p)
for n in ['BOM.md','ASSEMBLY_GUIDE.md','PRINT_PLAN.md','TEST_GUIDE.md','TEST_RECORD_TEMPLATE.csv','EXTERIOR_ASSEMBLY_REVISION.md','MODELING_BRIEF.md','GOOUU-BOARD-SPEC.md','package_delivery.py']:files.add(ROOT/n)
path=LOCAL/'EffMeet2_NOMI_布局A_v4_模型与图纸.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,p.relative_to(DESIGN))
with zipfile.ZipFile(path) as z:assert z.testzip() is None;count=len(z.namelist())
print(json.dumps({'zip':str(path),'entries':count,'bytes':path.stat().st_size,'manufacturing_release':False},ensure_ascii=False,indent=2))
