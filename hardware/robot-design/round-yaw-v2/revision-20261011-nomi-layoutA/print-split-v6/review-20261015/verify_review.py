"""Read-only review audit; never upgrades physical acceptance or writes canonical evidence."""
from pathlib import Path
import csv,json,struct,collections,re,hashlib,ast,subprocess,sys
ROOT=Path(__file__).resolve().parent;V6=ROOT.parent;HW=V6.parents[2];R1=ROOT/'face-retention-r1'
report={'scope':'documentation plus local candidate integrity only','manufacturing_ready':False,'hardware_validated':False,'checks':[]}
# Original verifier is run read-only, omitting its report-write expression.
p=V6/'verify_v6_delivery.py';tree=ast.parse(p.read_text(encoding='utf8'));tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='write_text')];exec(compile(tree,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'});report['checks'].append('canonical v6 original delivery verification passes; no report rewritten')
g=json.loads((R1/'production/geometry-review.json').read_text());assert g['status']=='PASS' and len(g['changed_parts'])==2 and not g['unexpected_changed_parts'] and not g['surface_intersections'];report['checks'].append('local R1 two changed parts; 29 unrelated parts equal; no nominal surface intersections')
# Re-read raw float32 candidate STL bytes, independent of Blender in-memory mesh.
exports=[]
for p in sorted((R1/'candidate-stl-local').glob('*.stl')):
 data=p.read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n
 edges=collections.Counter();ori=collections.Counter();signed=0;zero=0
 for i in range(n):
  a=struct.unpack_from('<12fH',data,84+50*i);vs=[a[3:6],a[6:9],a[9:12]]
  for u,v in [(vs[0],vs[1]),(vs[1],vs[2]),(vs[2],vs[0])]:
   k=tuple(sorted((u,v)));edges[k]+=1;ori[k]+=1 if u<v else -1
  u,v,w=vs;signed+=(u[0]*(v[1]*w[2]-v[2]*w[1])+u[1]*(v[2]*w[0]-v[0]*w[2])+u[2]*(v[0]*w[1]-v[1]*w[0]))/6
  d=[v[j]-u[j] for j in range(3)];e=[w[j]-u[j] for j in range(3)];cross=[d[1]*e[2]-d[2]*e[1],d[2]*e[0]-d[0]*e[2],d[0]*e[1]-d[1]*e[0]]
  zero+=sum(t*t for t in cross)<=1e-20
 assert all(v==2 for v in edges.values()) and all(v==0 for v in ori.values()) and signed>0 and zero==0,(p.name,signed,zero)
 exports.append({'file':p.name,'triangles':n,'closed':True,'signed_volume_mm3':round(signed,3),'zero_area':zero,'sha256':hashlib.sha256(data).hexdigest()})
assert len(exports)==2;report['candidate_exports']=exports;report['checks'].append('2 candidate STLs raw float32 edge incidence/orientation/positive volume/zero area checks pass')
bom=(HW/'round-yaw-v2/BOM.md').read_text(encoding='utf8');act=bom.split('## 12. 当前采购决策',1)[1]
for forbidden in ['必须外接 **INMP441×2 + MAX98357 + TP4056**','布局走 A（板在底座）','打印，不买（41 件','扩展板体积待实测后再定用不用','v5 MEASUREMENTS.csv','M3×70先取8支']:
 assert forbidden not in act,forbidden
rows=[s for s in act.splitlines() if re.match(r'^\| \*\*(?:E\d\d|M\d\d|C\d\d)\*\* \|',s)]
assert len(rows)==34
for id_ in ('E05','E16'):
 row=next(s for s in rows if s.startswith('| **'+id_+'**'));assert row.split('|')[3].strip()=='0',row
assert '| **E17**' in act and '31件' in act;report['checks'].append('single current BOM has 34 rows; E05/E16 zero; E17 unselected; v6 active old conflicts removed')
with (V6/'MEASUREMENTS.csv').open(encoding='utf-8-sig',newline='') as f:
 ms=list(csv.DictReader(f));assert len({r['id'] for r in ms})==len(ms)
 for r in ms:
  if r['id'] in ('FACE_RETENTION','FOOT_PAD'):assert r['status']=='UNVERIFIED' and not r['actual_mm']
report['checks'].append('new measurement rows remain unmeasured/unverified')
paths=[HW/'round-yaw-v2/BOM.md',HW/'HANDOFF.md',V6/'README.md',V6/'INTERFACE_GATES.md',R1/'README.md',ROOT/'FEEDBACK.md']
for p in paths:
 for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf8')):
  if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):continue
  assert (p.parent/link.split('#')[0]).exists(),(str(p),link)
report['checks'].append('changed Markdown local links exist')
report['status']='PASS';print(json.dumps(report,ensure_ascii=False,indent=2))
