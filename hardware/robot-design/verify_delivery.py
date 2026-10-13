"""Offline current-design audit. No Blender/firmware/hardware PASS implied."""
from pathlib import Path
import ast,json,re,csv,hashlib
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parents[1]
M=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'));checks=[]
for name,rel in M['canonical_files'].items():
 p=(ROOT/rel).resolve();assert p.is_relative_to(ROOT.resolve()) and p.is_file(),(name,rel)
checks.append('canonical active artifact paths exist')
P=json.loads((ROOT/M['canonical_files']['parameters']).read_text(encoding='utf-8'))
assert M['nominal_envelope_mm']==P['envelope'] and M['nominal_yaw_limits_deg']==P['yaw']['range_deg']
assert M['stage']=='reversible_blockout' and not any(M[k] for k in ['manufacturing_ready','hardware_validated','final_design_approved'])
assert P['hardware_platform'].startswith('GOOUU') and P['layout']=='A2' and 'PLA Matte' in P['print_material']['body']
checks.append('GOOUU/layoutA2/PLA source parameters and unreleased stage agree')
B=(ROOT/M['canonical_files']['bom']).read_text(encoding='utf-8');S=B.split('## 12.',1)[1].split('## 官方来源',1)[0]
ids=re.findall(r'^\| \*\*([EMC]\d\d)\*\* \|',S,re.M)
assert len(ids)==33 and len(set(ids))==33
assert all(s in S for s in ['GOOUU','HSD028309','INMP441','MAX98357','TP4056','禁止裁剪FPC','188mm'])
checks.append('33 canonical BOM IDs include current board/display/v6 2:1 drive and safe FPC handling')
REV=ROOT/'round-yaw-v2/revision-20261011-nomi-layoutA'
mesh=json.loads((REV/'production/evaluated-shells.json').read_text(encoding='utf-8'))
assert len(mesh)==5
for n,s in mesh.items():assert not any(s[k] for k in ['boundary_edges','nonmanifold_edges','loose_edges','zero_area_faces']) and s['components']==1,n
assert mesh['N4_HEAD_SHELL']['bounds_mm'][1][2]<=222.05
bounds=mesh['N4_FACE_PANEL']['bounds_mm'];size=[bounds[1][i]-bounds[0][i] for i in range(3)]
assert abs(size[1]-2.4)<.05 and abs(size[2]-106)<.05
checks.append('5 historical v4 closed shells, one component each, vertical106mm face and actual222mm height bound')
fit=json.loads((REV/'production/nominal-fit.json').read_text(encoding='utf-8'));assert fit['all_inside'] and len(fit['components'])==15 and not fit['hardware_validated']
yaw=json.loads((REV/'production/yaw-candidate-audit.json').read_text(encoding='utf-8'));assert {p['angle_deg'] for p in yaw['poses']}=={-45,0,45}
assert all(p['nonmanifold_edges']==0 and p['shell_to_lid_min_vertical_gap_mm']>=13.99 for p in yaw['poses'])
volumes=[p['head_volume_mm3'] for p in yaw['poses']];assert (max(volumes)-min(volumes))/max(volumes)<1e-5
assert json.loads((REV/'production/protected-scene-check.json').read_text(encoding='utf-8'))['unchanged']
checks.append('historical v4 15 nominal boxes and3 yaw poses scoped-pass; earlier object data preserved; no flex-life claim')
with (ROOT/M['canonical_files']['test_record_template']).open(encoding='utf-8-sig',newline='') as f:records=list(csv.DictReader(f))
assert len(records)==26 and {r['test_id'] for r in records}=={f'T{i:02d}' for i in range(1,27)}
assert all(r['status']=='NOT_RUN' and not r['actual_result'] and not r['executed_at'] for r in records)
checks.append('26 unexecuted hardware test records preserved')
count=0
active=[REPO/'README.md',ROOT/'README.md',ROOT/'HANDOFF.md',ROOT/'round-yaw-v2/README.md']+list(REV.glob('*.md'))+list((REV/'print-split-v6').glob('*.md'))+[ROOT/'round-yaw-v2'/n for n in ['BOM.md','ASSEMBLY_GUIDE.md','PRINT_PLAN.md','TEST_GUIDE.md','EXTERIOR_ASSEMBLY_REVISION.md','MODELING_BRIEF.md']]
for p in active:
 for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
  link=link.split('#',1)[0]
  if link:assert (p.parent/link).exists(),f'{p.relative_to(REPO)} -> {link}';count+=1
checks.append(f'{count} current local documentation links resolve')
for p in ROOT.rglob('*.py'):
 if 'local-only' not in p.parts:ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
for rel,sha in M['artifact_sha256'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha,rel
binding=json.loads((REV/'production/source-binding.json').read_text(encoding='utf-8'))
assert binding['parameters_sha256']==hashlib.sha256((REV/'print-split-v5/parameters-v4-frozen.json').read_bytes()).hexdigest()
assert binding['generator_sha256']==hashlib.sha256((REV/'update_nomi_layoutA.py').read_bytes()).hexdigest()
checks.append('helpers parse and artifact hashes match; historical v4 binding uses frozen parameters')
import subprocess,sys
subprocess.run([sys.executable,str(REV/'print-split-v6/verify_v6_delivery.py')],check=True)
checks.append('current v6 31-part candidate delivery checks passed; no slice/print/hardware tests implied')
print(json.dumps({'status':'PASS','checks':checks,'scope':'offline current design delivery only','firmware_tests_run':False,'hardware_tests_run':False,'manufacturing_release':False},ensure_ascii=False,indent=2))
