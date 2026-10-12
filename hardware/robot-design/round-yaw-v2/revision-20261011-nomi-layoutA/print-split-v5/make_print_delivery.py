"""Mesh-only 3MF start plates; no slicer/toolpath or manufacturing release."""
from pathlib import Path
import json,struct,zipfile,hashlib,csv,math
import xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROD=ROOT/'production';PLATES=ROOT/'plate-start-layouts';PLATES.mkdir(exist_ok=True)
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def read_stl(path):
 data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n
 vertices=[];faces=[];lookup={}
 for i in range(n):
  values=struct.unpack_from('<12fH',data,84+50*i);face=[]
  for j in range(3):
   point=tuple(values[3+j*3:6+j*3])
   if point not in lookup:lookup[point]=len(vertices);vertices.append(point)
   face.append(lookup[point])
  faces.append(face)
 edges={};vol=0
 for a,b,c in faces:
  assert len({a,b,c})==3,f'collapsed STL triangle: {path.name}'
  for u,v in ((a,b),(b,c),(c,a)):
   key=tuple(sorted((u,v)));edges[key]=edges.get(key,0)+1
  x,y,z=vertices[a],vertices[b],vertices[c];vol+=(x[0]*(y[1]*z[2]-y[2]*z[1])-x[1]*(y[0]*z[2]-y[2]*z[0])+x[2]*(y[0]*z[1]-y[1]*z[0]))/6
 assert all(v==2 for v in edges.values()),'not watertight after float32 export'
 assert vol>0,'nonpositive volume'
 return vertices,faces,vol
j=json.loads((ROOT/'parts.json').read_text(encoding='utf8'));rows=j['parts'];meshes={};checks=[]
for r in rows:
 if 'stl' not in r:continue
 vertices,faces,vol=read_stl(ROOT/r['stl']);meshes[r['id']]=(vertices,faces)
 checks.append({'id':r['id'],'triangles':len(faces),'watertight':True,'signed_volume_mm3':vol,'sha256':hashlib.sha256((ROOT/r['stl']).read_bytes()).hexdigest()})
def pack(group,items):
 result=[];index=1;current=[];x=y=8;rowheight=0
 for r in sorted(items,key=lambda r:r['print_size_mm'][1],reverse=True):
  w,d,_=r['print_size_mm'];assert w<=240 and d<=240
  if x+w>248:x=8;y+=rowheight+8;rowheight=0
  if y+d>248:
   result.append({'id':group+'-'+str(index),'parts':current,'color':items[0]['color']});index+=1;current=[];x=y=8;rowheight=0
  current.append({'part_id':r['id'],'x':x,'y':y,'size_mm':r['print_size_mm']});x+=w+8;rowheight=max(rowheight,d)
 if current:result.append({'id':group+'-'+str(index),'parts':current,'color':items[0]['color']})
 return result
plates=[]
for group in ('G1','G2','G3','B1','B2','B3'):
 items=[r for r in rows if r['plate_group']==group and r['id'] in meshes]
 if items:plates+=pack(group,items)
plate_by_part={item['part_id']:p['id'] for p in plates for item in p['parts']}
for r in rows:r['plate_start']=plate_by_part.get(r['id'],'BLOCKED_NO_EXPORT')
ns='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',ns)
def tag(t):return '{'+ns+'}'+t
for plate in plates:
 model=ET.Element(tag('model'),{'unit':'millimeter','xml:lang':'en-US'});ET.SubElement(model,tag('metadata'),{'name':'Title'}).text='EffMeet2 '+plate['id']+' UNVERIFIED'
 ET.SubElement(model,tag('metadata'),{'name':'Description'}).text='Geometry only. Not sliced. Not printed. Not released.'
 resources=ET.SubElement(model,tag('resources'));build=ET.SubElement(model,tag('build'))
 for i,item in enumerate(plate['parts'],1):
  pid=item['part_id'];verts,faces=meshes[pid];o=ET.SubElement(resources,tag('object'),{'id':str(i),'type':'model','name':pid+'_UNVERIFIED'});mesh=ET.SubElement(o,tag('mesh'));vs=ET.SubElement(mesh,tag('vertices'));ts=ET.SubElement(mesh,tag('triangles'))
  for v in verts:ET.SubElement(vs,tag('vertex'),dict(zip(('x','y','z'),(format(n,'.8g') for n in v))))
  for f in faces:ET.SubElement(ts,tag('triangle'),dict(zip(('v1','v2','v3'),(str(n) for n in f))))
  ET.SubElement(build,tag('item'),{'objectid':str(i),'transform':f'1 0 0 0 1 0 0 0 1 {item["x"]:.5f} {item["y"]:.5f} 0'})
 path=PLATES/(plate['id']+'_UNSLICED_START.3mf')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
  z.writestr('3D/3dmodel.model',ET.tostring(model,encoding='utf-8',xml_declaration=True))
 plate['file']='plate-start-layouts/'+path.name;plate['status']='START_NOT_SLICED';plate['bed_mm']=[256,256]
dump(PROD/'export-byte-audit.json',{'status':'PASS','scope':'binary STL edge test only, not fit/strength','count':len(checks),'parts':checks})
samples=[{'id':'S1','material':'现有PETG','parts':['P07','P08','P15','P03','P18','P20','P21','P22'],'test':'6806夹紧/轴D接收/舵盘口袋及真带齿槽/滑盖间隙'},{'id':'S2','material':'正式黑PLA Matte','parts':['P07','P08','P15','P03','P18','P20','P21','P22','P02'],'test':'同接口换正式料复测；圆面板表面/屏可视区/相机窗口'}]
for s in samples:s['status']='NOT_SLICED_NOT_PRINTED';s['machine']='自有A1'
j['parts']=rows;j['start_plate_count']=len(plates);dump(ROOT/'parts.json',j)
dump(ROOT/'plate-start-layouts.json',{'status':'START_NOT_SLICED','plates_frozen':False,'plate_count':len(plates),'formal_start_plates':plates,'sample_batches':samples,'note':'样片也可能分多盘；最终朝向、盘数、支撑和耗时须实际切片＋实打回填'})
fields=['id','name','quantity','material','color','interface_status','size_mm','print_size_mm','orientation_euler_deg','orientation_status','support_start','plate_start','stl','slicer_status','sample_print_status','release_status']
with (ROOT/'PARTS.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
lines=['# v5 独立打印候选件表','',f'**{len(rows)}件装配件 / {len(meshes)}个闭合候选STL / {len(plates)}张正式几何起点盘。** 件数来自实际结构；盘数、朝向、支撑未冻结。','','**全部 UNVERIFIED / NOT_SLICED_NOT_PRINTED / CANDIDATE_NOT_RELEASED。** 闭合网格不证明实物配合、强度或功能合格。','','原生模型保留装配坐标。STL采用朝向起点、最低点归零、mm单位。3MF只有几何，没有打印机配置、支撑或G-code。','','|件号|件名|数量|材料色|装配尺寸mm|朝向起点XYZ°|支撑建议|起点盘|接口/打印状态|','|---|---|---:|---|---|---|---|---|---|']
for r in rows:
 size=' × '.join(f'{v:.2f}' for v in r['size_mm']);ori='/'.join(str(v) for v in r['orientation_euler_deg']);name=f'[{r["name"]}]({r["stl"]})' if 'stl' in r else r['name']+'（阻塞未导出）'
 lines.append(f'|{r["id"]}|{name}|1|{r["material"]} {r["color"]}|{size}|{ori}|{r["support_start"]}|{r["plate_start"]}|unverified / 未切片未实打|')
lines+=['','## 起点盘（不是切片文件）','']+[f'- [{p["id"]}]({p["file"]})：'+', '.join(x['part_id'] for x in p['parts']) for p in plates]+['','## 样片批次','']+[f'- **{s["id"]}** {s["material"]}：'+', '.join(s['parts'])+'。'+s['test']+'；直接以这些真实件作为样片。' for s in samples]
lines+=['','## 明确薄壁例外','','一般壳壁预算2.4mm。轴承挡唇1.0mm、带轮法兰1.2mm、隐私滑片1.6mm/压框1.2mm、键帽2.0mm是候选薄壁例外，不声称满足2.4mm。0.4喷嘴实际路径和功能须预览＋样片。','','轴承座分缝朝平台只是试切起点；必须同时验孔形、夹紧方向与层间强度。没有实物验证的最终朝向字段保持空。','']
(ROOT/'PARTS.md').write_text('\n'.join(lines),encoding='utf8')
font_path='C:/Windows/Fonts/msyh.ttc';font=ImageFont.truetype(font_path,22);small=ImageFont.truetype(font_path,16)
W=1800;H=240+560*math.ceil(len(plates)/3);im=Image.new('RGB',(W,H),'#efefea');d=ImageDraw.Draw(im)
d.text((55,32),'EffMeet2 · v5 独立候选件 / 预排盘',font=ImageFont.truetype(font_path,38),fill='#202b31');d.text((55,92),f'{len(rows)}件装配件 · {len(plates)}张正式几何起点盘 · NOT SLICED / NOT RELEASED',font=font,fill='#86502b');d.text((55,132),'最终朝向、支撑与盘数须切片预览＋样片实打。下图只是包围尺寸示意。',font=font,fill='#4b585e')
for index,plate in enumerate(plates):
 x0=55+(index%3)*570;y0=205+(index//3)*560;scale=1.65;d.text((x0,y0),plate['id']+' / '+plate['color'],font=font,fill='#263c46');ox=x0;oy=y0+40;d.rectangle((ox,oy,ox+256*scale,oy+256*scale),fill='#fafbf8',outline='#98a4aa',width=2)
 for item in plate['parts']:
  x=ox+item['x']*scale;y=oy+item['y']*scale;w,h,_=item['size_mm'];d.rounded_rectangle((x,y,x+w*scale,y+h*scale),radius=3,fill='#465761' if plate['color']=='黑' else '#b8c4c8',outline='#24363f');d.text((x+3,y+2),item['part_id'],font=small,fill='white' if plate['color']=='黑' else '#10242e')
 d.text((x0,y0+478),'256×256mm / 间距8mm / 包围轮廓起点',font=small,fill='#5c6870')
im.save(ROOT/'plate-start-layouts.png')
print(json.dumps({'parts':len(rows),'exports':len(meshes),'start_plates':len(plates),'status':'GEOMETRY_ONLY'},ensure_ascii=False))

