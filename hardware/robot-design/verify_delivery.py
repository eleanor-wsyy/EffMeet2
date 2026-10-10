"""Offline handoff checks. Does not import Blender or claim hardware validation."""
from pathlib import Path
import ast,json,re,hashlib,csv
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
checks=[]
for name,rel in manifest['canonical_files'].items():
    f=(ROOT/rel).resolve();assert f.is_relative_to(ROOT.resolve()) and f.is_file(),(name,rel)
checks.append('manifest canonical paths exist and remain inside design folder')
P=json.loads((ROOT/'round-yaw-v2/parameters.json').read_text(encoding='utf-8'))
assert manifest['nominal_envelope_mm']==P['envelope']
assert manifest['nominal_yaw_limits_deg']==P['yaw']['range_deg']
assert manifest['stage']=='reversible_blockout' and not any(manifest[k] for k in ['final_design_approved','manufacturing_ready','hardware_validated'])
checks.append('manifest agrees with source parameters and unreleased stage')
bom=(ROOT/'round-yaw-v2/BOM.md').read_text(encoding='utf-8')
ids=re.findall(r'^\| ([EMC]\d\d) \|',bom,re.M)
assert len(ids)==30 and len(set(ids))==30
checks.append('one current BOM contains 30 unique material entries')
explained=re.findall(r'^#### ([EMC]\d\d) ',bom,re.M)
assert len(explained)==30 and set(explained)==set(ids)
for part in re.split(r'^#### [EMC]\d\d ',bom,flags=re.M)[1:]:
    assert all(label in part for label in ['**具体功能：**','**直接效果：**','**最终目标/验收：**'])
checks.append('all 30 material IDs have function, direct effect and final acceptance explanations')
final_section=bom.split('## 12.',1)[1].split('## 官方来源',1)[0]
final_ids=re.findall(r'^\| \*\*([EMC]\d\d)\*\* \|',final_section,re.M)
assert len(final_ids)==30 and set(final_ids)==set(ids)
plan=(ROOT/'round-yaw-v2/PRINT_PLAN.md').read_text(encoding='utf-8')
assert 'ABS-GF' in plan and '不是已经存在的可打印文件' in plan
checks.append('all 30 IDs have final procurement decisions and a non-released print plan')
active=[ROOT/'round-yaw-v2/EXTERIOR_ASSEMBLY_REVISION.md',ROOT/'round-yaw-v2/concept/nomi-aligned-20261010/SOURCE.md',ROOT/'round-yaw-v2/ASSEMBLY_GUIDE.md',ROOT/'round-yaw-v2/TEST_GUIDE.md',ROOT/'round-yaw-v2/PRINT_PLAN.md',ROOT/'round-yaw-v2/BOM.md',ROOT/'README.md',ROOT/'HANDOFF.md',ROOT/'round-yaw-v2/README.md',ROOT/'archive/README.md',ROOT/'archive/procurement/README.md',REPO/'README.md',REPO/'docs/handoff/README.md',REPO/'docs/handoff/2026-10-10-robot-design-and-bom.md',REPO/'docs/handoff/2026-10-05-hardware-purchase-list.md',REPO/'docs/handoff/2026-10-05-final-handoff.md',REPO/'docs/handoff/2026-10-07-装配联调计划.md',REPO/'hardware/electronics/README.md',REPO/'hardware/enclosure/README.md',REPO/'hardware/enclosure/EffMeet2_外壳说明_v2.md',REPO/'assets/enclosure/README.md']
count=0
for f in active:
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
        target=link.split('#',1)[0]
        if target:
            assert (f.parent/target).exists(),f'{f.relative_to(REPO)} -> {link}'
            count+=1
checks.append(f'{count} local links in active/compatibility documents resolve')
with (ROOT/'round-yaw-v2/TEST_RECORD_TEMPLATE.csv').open(encoding='utf-8-sig',newline='') as f:
    records=list(csv.DictReader(f))
assert len(records)==26 and {r['test_id'] for r in records}=={f'T{i:02d}' for i in range(1,27)}
assert all(r['status']=='NOT_RUN' and not r['actual_result'] and not r['executed_at'] for r in records)
guide=(ROOT/'round-yaw-v2/TEST_GUIDE.md').read_text(encoding='utf-8')
assert set(re.findall(r'^\| (T\d\d) \|',guide,re.M))=={r['test_id'] for r in records}
checks.append('26 test cases match the untouched NOT_RUN template; no hardware pass fabricated')
for name in ['ASSEMBLY_GUIDE.md','PRINT_PLAN.md','TEST_GUIDE.md','BOM.md']:
    assert 'EXTERIOR_ASSEMBLY_REVISION.md' in (ROOT/'round-yaw-v2'/name).read_text(encoding='utf-8'),name
assert manifest['latest_visual']['hardware_changed'] is False and manifest['latest_visual']['cad_changed'] is False
checks.append('current exterior revision is referenced by assembly/print/test/BOM, without false CAD completion')
for f in (ROOT/'round-yaw-v2').glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),filename=str(f))
checks.append('current Python helper scripts parse without importing optional dependencies')
fit=json.loads((ROOT/'round-yaw-v2/fit-report.json').read_text(encoding='utf-8'))
raw=json.loads((ROOT/'round-yaw-v2/production/evaluated_mesh_validation.json').read_text(encoding='utf-8'))
final=json.loads((ROOT/'round-yaw-v2/production/validation_report.json').read_text(encoding='utf-8'))
yaw=json.loads((ROOT/'round-yaw-v2/production/yaw-dependency-audit.json').read_text(encoding='utf-8'))
assert fit['all_inside'] and fit['all_pairs_separated'] and len(fit['components'])==6
assert raw['overall_status']=='PASS' and yaw['status']=='PASS'
assert final['overall_status']=='WARN' and final['formal_production_release'] is False
checks.append('existing scoped geometry evidence preserved without manufacturing approval')
for f in [ROOT/manifest['canonical_files']['model'],ROOT/'archive/seat-card-v1/EffMeet2_席位牌_封装布局_v1_审阅.blend']:
    assert f.read_bytes().startswith((b'BLENDER',bytes.fromhex('28b52ffd'),bytes.fromhex('1f8b'))),f.name
for rel,expected in manifest['artifact_sha256'].items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==expected,rel
checks.append('Blender containers and frozen artifact/source SHA256 hashes match')
print(json.dumps({'status':'PASS','checks':checks,'software_tests_rerun':False,'hardware_tests_run':False},ensure_ascii=False,indent=2))
