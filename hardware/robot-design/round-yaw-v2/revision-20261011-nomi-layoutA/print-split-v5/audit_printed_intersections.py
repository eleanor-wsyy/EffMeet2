"""Nominal printed-part intersection audit; no actual hardware or print tolerance acceptance."""
from pathlib import Path
import sys,json,itertools,numpy as np
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parents[1]/'local-only/mesh-tools'));import manifold3d as md
raw=json.loads((ROOT.parents[1]/'local-only/v5-native-export-meshes.json').read_text());parts={p['id']:p for p in json.loads((ROOT/'parts.json').read_text())['parts']};models={};bounds={}
for pid,r in raw['meshes'].items():
 v=np.array(r['vertices'],dtype=np.float64);f=np.array(r['triangles'],dtype=np.uint64);models[pid]=md.Manifold(md.Mesh64(v,f,tolerance=.0001));bounds[pid]=(v.min(axis=0),v.max(axis=0))
issues=[];checks=0
for a,b in itertools.combinations(models,2):
 if np.any(np.minimum(bounds[a][1],bounds[b][1])-np.maximum(bounds[a][0],bounds[b][0])<=.0001):continue
 checks+=1;intersection=models[a]^models[b];vol=intersection.volume()
 if vol>.01:issues.append({'a':a,'a_name':parts[a]['name'],'b':b,'b_name':parts[b]['name'],'intersection_volume_mm3':vol})
(ROOT/'production/nominal-printed-intersections.json').write_text(json.dumps({'scope':'native nominal printed volumes only, not hardware/support/tolerance verification','bbox_candidates_checked':checks,'positive_intersections':issues,'manufacturing_ready':False},ensure_ascii=False,indent=2),encoding='utf8')
for i in issues:print(i,flush=True)
