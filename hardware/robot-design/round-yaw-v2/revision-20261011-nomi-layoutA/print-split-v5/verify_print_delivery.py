"""Offline candidate delivery audit; no sliced/printed/hardware/manufacturing PASS implied."""
from pathlib import Path
import json,hashlib,struct,zipfile,xml.etree.ElementTree as ET,csv,ast,re
ROOT=Path(__file__).resolve().parent;P=json.loads((ROOT/'../../parameters.json').resolve().read_text(encoding='utf8'));d=json.loads((ROOT/'parts.json').read_text(encoding='utf8'));rows=d['parts'];checks=[]
assert len(rows)==41 and len({r['id'] for r in rows})==41
for r in rows:
 assert r['quantity']==1 and r['interface_status']=='unverified' and r['release_status']=='CANDIDATE_NOT_RELEASED'
 assert r['slicer_status']==r['sample_print_status']=='NOT_RUN'
 assert not any(t in r['object'] for t in ('PROXY','KEEP_OUT','ENVELOPE'))
 data=(ROOT/r['stl']).read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n and n>0
 assert hashlib.sha256(data).hexdigest()==r['stl_sha256']
 for i in range(n):
  x=struct.unpack_from('<12fH',data,84+i*50);a=x[3:6];b=x[6:9];c=x[9:12];u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)];cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];assert sum(q*q for q in cross)>0,(r['id'],i)
checks.append('41 true independent candidate STLs, byte hashes and nonzero32bit triangles')
byte=json.loads((ROOT/'production/export-byte-audit.json').read_text());assert byte['status']=='PASS' and byte['count']==41 and all(x['watertight'] and x['signed_volume_mm3']>0 for x in byte['parts']);checks.append('re-read32bit topology edges all paired and positive oriented volume')
plates=json.loads((ROOT/'plate-start-layouts.json').read_text(encoding='utf8'));assert not plates['plates_frozen'];seen=[];ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
for p in plates['formal_start_plates']:
 with zipfile.ZipFile(ROOT/p['file']) as z:
  assert z.testzip() is None;model=ET.fromstring(z.read('3D/3dmodel.model'));assert model.attrib['unit']=='millimeter';objs=model.findall('m:resources/m:object',ns);assert len(objs)==len(p['parts'])
  for o in objs:
   vv=o.findall('m:mesh/m:vertices/m:vertex',ns);ff=o.findall('m:mesh/m:triangles/m:triangle',ns);assert vv and ff
   assert all(0<=int(f.attrib[k])<len(vv) for f in ff for k in ('v1','v2','v3'))
 for q in p['parts']:
  assert q['x']>=8 and q['y']>=8 and q['x']+q['size_mm'][0]<=248.01 and q['y']+q['size_mm'][1]<=248.01;seen.append(q['part_id'])
assert sorted(seen)==sorted(r['id'] for r in rows);checks.append('geometry-only3MFs valid, each part included once,256mm budget arrangement; NOT sliced')
binding=json.loads((ROOT/'production/source-binding.json').read_text())
for field,path in [('parameters_sha256',ROOT/'../../parameters.json'),('generator_sha256',ROOT/'build_print_split.py'),('model_sha256',ROOT/'EffMeet2_NOMI_布局A_v5_拆件候选.blend'),('export_finalize_source_sha256',ROOT/'finalize_exports.py'),('extract_source_sha256',ROOT/'extract_export_meshes.py')]:assert hashlib.sha256(path.resolve().read_bytes()).hexdigest()==binding[field],field
assert json.loads((ROOT/'production/protected-scene-check.json').read_text())['unchanged'];checks.append('native source binding and164 protected original objects unchanged')
yaw=json.loads((ROOT/'production/yaw-audit.json').read_text());assert {r['angle_deg'] for r in yaw['poses']}=={-45,0,45};assert all(r['head_min_z_mm']>=91.99 and r['gap_from_original_lid_crown_mm']>=13.99 for r in yaw['poses']);vol=[r['volume_mm3'] for r in yaw['poses']];pose_volume_delta=(max(vol)-min(vol))/max(vol)
issues=json.loads((ROOT/'production/nominal-printed-intersections.json').read_text(encoding='utf8'))['positive_intersections'];assert not issues,issues;checks.append('neutral printed-part intersections cleared above0.01mm3;3 yaw poses keep head14mm gap; no hardware proof')
with (ROOT/'SLICER_CHECKLIST.csv').open(encoding='utf-8-sig',newline='') as f:sl=list(csv.DictReader(f))
assert len(sl)==41 and all(r['status']=='NOT_RUN' and not r['final_orientation'] and not r['slicer_evidence'] and not r['sample_evidence'] for r in sl)
for p in ROOT.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in ROOT.glob('*.md'):
 for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf8')):
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
  assert (p.parent/link.split('#')[0]).exists(),(p.name,link)
checks.append('41 blank slicer/sample records, active links and source syntax checked')
report={'status':'PASS','scope':'offline conditional geometry delivery only','checks':checks,'parts':41,'start_plates':plates['plate_count'],'slicer_tests_run':False,'sample_prints_run':False,'hardware_tests_run':False,'manufacturing_ready':False,'warnings':(['Native pose Boolean volume differs by '+str(pose_volume_delta*100)+' percent; rig is NOT validated. Final neutral STL checks are separate.'] if pose_volume_delta>1e-5 else [])}
(ROOT/'production/delivery-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False,indent=2))
