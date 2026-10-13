"""Offline v6 candidate delivery audit; no slicer/print/hardware/manufacturing PASS implied."""
from pathlib import Path
import json,hashlib,struct,csv,ast,re
ROOT=Path(__file__).resolve().parent;PJ=(ROOT/'../../parameters.json').resolve();P=json.loads(PJ.read_text(encoding='utf8'))
d=json.loads((ROOT/'parts.json').read_text(encoding='utf8'));rows=d['parts'];checks=[];N=len(rows)
assert d['revision']=='v6' and d['layout']=='A2' and not d['manufacturing_ready'] and not d['hardware_validated'] and not d['plates_frozen']
assert N==31 and len({r['id'] for r in rows})==N
blend=ROOT/'EffMeet2_NOMI_布局A_v6_紧凑候选.blend';assert d['model_sha256']==hashlib.sha256(blend.read_bytes()).hexdigest(),'STLs not exported from current blend'
for r in rows:
 assert r['quantity']==1 and r['interface_status']=='unverified' and r['release_status']=='CANDIDATE_NOT_RELEASED' and r['slicer_status']==r['sample_print_status']=='NOT_RUN'
 assert not any(t in r['object'] for t in ('PROXY','KEEP_OUT','ENVELOPE','GROUND','EYE')) and r['fits_256_bed']
 data=(ROOT/r['stl']).read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n and n>0 and hashlib.sha256(data).hexdigest()==r['stl_sha256'],r['id']
 assert r['plate_start']==('GREY' if r['object'] in ('N6_HEAD_SHELL','N6_BASE_CUP','N6_BASE_LID') else 'BLACK')
stls=sorted(p.name for p in (ROOT/'candidate-stl').glob('*.stl'));assert stls==sorted(Path(r['stl']).name for r in rows),'stray STL'
checks.append(f'{N} candidate STLs: hashes, sizes, no proxy/keep-out, grey/black grouping, all fit 256 bed')
b=json.loads((ROOT/'production/export-byte-audit.json').read_text());assert b['status']=='PASS' and b['count']==N and all(x['watertight'] and x['signed_volume_mm3']>0 and not x['collapsed'] and not x['zero_area'] for x in b['parts'])
checks.append('float32 STL re-read: all closed, positive volume')
s=json.loads((ROOT/'production/stage1-checks.json').read_text(encoding='utf8'))
assert not s['manufacturing_ready'] and not s['hardware_validated']
for k,v in s['shell_stats'].items():assert v['nonmanifold_edges']==0 and v['boundary_edges']==0 and v['components']==1 and v['volume_mm3']>0,k
assert not s['overlap_part_part'] and not s['overlap_part_proxy'] and all(c['inside'] for c in s['proxy_containment'])
assert {y['deg'] for y in s['yaw']}=={-45,0,45} and all(not y['rot_vs_fixed'] for y in s['yaw'])
q=s['params'];assert q['camera_fpc_span_mm']<=11 and q['camera_fpc_slack_mm']>=3
bt=s['belt'];assert bt['picked']['L']==188 and abs(bt['L_check']-188)<.01 and bt['ratio']==2 and bt['servo_pm90_to_head_deg']==45
checks.append('5 shells 0/0/1, 0 part/part & part/proxy overlaps, proxies contained, 3 yaw poses clear, FPC slack>=3, belt 188 2:1')
assert P['layout']=='A2' and P['revision'].startswith('nomi-goouu-layoutA2-v6') and not P['manufacturing_ready'] and not P['hardware_validated']
assert P['print_split']['pulley']['belt_length']==188 and P['envelope']['width']<=153.01
frozen=ROOT/'parameters-v5-frozen.json';v5b=json.loads((ROOT/'../print-split-v5/production/source-binding.json').read_text())
assert hashlib.sha256(frozen.read_bytes()).hexdigest()==v5b['parameters_sha256'];checks.append('parameters.json is v6/A2; v5 frozen copy matches v5 binding')
with (ROOT/'PARTS.csv').open(encoding='utf-8-sig',newline='') as f:pc=list(csv.DictReader(f))
assert len(pc)==N and all(r['slicer_status']=='NOT_RUN' and r['sample_print_status']=='NOT_RUN' for r in pc)
with (ROOT/'MEASUREMENTS.csv').open(encoding='utf-8-sig',newline='') as f:ms={r['id']:r for r in csv.DictReader(f)}
assert ms['TP4056']['status']==ms['BATTERY']['status']=='DEFERRED' and 'USB_C_POWER_BOARD' in ms and 'CROSS_YAW_WIRES' in ms
for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in ROOT.glob('*.md'):
 for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf8')):
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
  assert (p.parent/link.split('#')[0]).exists(),(p.name,link)
checks.append('PARTS.csv/MEASUREMENTS.csv records, source syntax and md links checked')
rep={'status':'PASS','scope':'offline v6 conditional geometry delivery only','checks':checks,'parts':N,'slicer_tests_run':False,'sample_prints_run':False,'hardware_tests_run':False,'manufacturing_ready':False}
(ROOT/'production/delivery-validation.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(rep,ensure_ascii=False,indent=2))
