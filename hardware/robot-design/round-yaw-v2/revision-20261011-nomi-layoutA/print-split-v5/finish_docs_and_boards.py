"""Label true model renders, generate synchronized candidate review boards and blank test fields."""
from pathlib import Path
import json,csv,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;REN=ROOT/'renders';DRAW=ROOT/'drawings';DRAW.mkdir(exist_ok=True);rows=json.loads((ROOT/'parts.json').read_text(encoding='utf8'))['parts'];fontpath='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(fontpath,n)
raw=Image.open(REN/'06_parts_index_raw.png').convert('RGB');W,H=raw.size;im=Image.new('RGB',(W,H+170),'#eeeeea');im.paste(raw,(0,130));d=ImageDraw.Draw(im);d.text((58,20),'EffMeet2 / NOMI · v5 · 41件候选索引',font=font(40),fill='#243944');d.text((58,76),'真实评估几何 · 每件为便于阅读各自缩放 · 非工程比例图 · NOT RELEASED',font=font(25),fill='#78562e')
labels=json.loads((ROOT/'production/part-index-labels.json').read_text())
for pid,(x,y,z) in labels.items():d.text((x*W-28,(1-y)*H+130),pid,font=font(26),fill='#152e3b',stroke_width=2,stroke_fill='#eeeeee')
im.save(REN/'06_parts_index.png')
def canvas(title,subtitle):
 a=Image.new('RGB',(1800,1200),'#eeeFec');dr=ImageDraw.Draw(a);dr.text((50,28),title,font=font(38),fill='#273945');dr.text((50,88),subtitle,font=font(21),fill='#6c563c');dr.line((50,113,1750,113),fill='#b6c0c2',width=2);return a,dr
def fit(image,w,h):
 image=image.copy();image.thumbnail((w,h),Image.Resampling.LANCZOS);return image
hero,dh=canvas('01 / NOMI圆头 · 灰黑PLA Matte · 真实模型','工程候选：预算接收、独立分件、可继续试切与样片；没有实物/制造放行')
x=fit(Image.open(REN/'01_hero_candidate.png'),1280,960);hero.paste(x,(40,130));dh.text((1340,195),'CMF / 裸打',font=font(32),fill='#243944')
for i,(color,text) in enumerate([('#b6bbbc','灰 PLA Matte / 头壳与底座'),('#283239','黑 PLA Matte / 圆脸与结构')]):dh.rectangle((1340,285+i*150,1410,355+i*150),fill=color);dh.text((1340,370+i*150),text,font=font(19),fill='#394b56')
for i,t in enumerate(['普通LCD，仅屏面有光泽','Ø106圆黑脸，无透明整罩','固定底座，头部软件±45°','热/强度/噪声与实际色仍待测']):dh.text((1340,635+i*60),t,font=font(20),fill='#394b56')
dh.text((50,1150),'N5_PRINT_SPLIT_CANDIDATE / 概念质感照明，不替代PLA样片、屏驱动或舵机验收',font=font(22),fill='#6a563f');hero.save(DRAW/'01_主视觉_CMF_v5.png')
ortho,dd=canvas('02 / 外观与名义尺寸 · v5','180W × 164D × 222H mm / Ø106圆面板 / 截平后头部净高约130mm / 顶冠至头底14mm')
for name,xpos in [('02_front_candidate.png',35),('03_side_candidate.png',620),('04_top_candidate.png',1205)]:
 x=fit(Image.open(REN/name),560,940);ortho.paste(x,(xpos,195))
for t,xpos in [('正视 / 宽180mm',70),('侧视 / 底座深164mm',650),('俯视 / 椭圆底座',1240)]:dd.text((xpos,1000),t,font=font(25),fill='#294554')
dd.text((50,1150),'显示/舵盘/板模组接口是预算；尺寸来自当前参数与实际模型，未做切片、实打或公差放行',font=font(22),fill='#6a563f');ortho.save(DRAW/'02_视图与尺寸_v5.png')
internal,di=canvas('03 / 承力结构与独立件 · v5','双轴承承力塔＋分体座＋中空轴＋带轮 / 原生模型的候选结构，不是已验收总成')
x=fit(Image.open(REN/'05_internal_candidate.png'),960,960);internal.paste(x,(35,150));x=fit(Image.open(REN/'06_parts_index.png'),790,900);internal.paste(x,(990,170));di.text((50,1140),'41件真实打印几何；采购件为尺寸预算代理且从STL排除。接口、层向、齿带与实际功能需测试。',font=font(22),fill='#6a563f');internal.save(DRAW/'03_结构与独立件_v5.png')
with (ROOT/'SLICER_CHECKLIST.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['part_id','name','start_orientation','start_plate','actual_printer','profile','layer_mm','final_orientation','support','slicer_evidence','sample_evidence','measured_result','status'])
 for r in rows:w.writerow([r['id'],r['name'],r['orientation_euler_deg'],r['plate_start'],'','','','','','','','','NOT_RUN'])
# Synchronize factual coordinates in v5 guides only; historical v4 docs remain historical.
for name in ('README.md','ASSEMBLY.md'):
 p=ROOT/name;s=p.read_text(encoding='utf8').replace('(20,-36,25)','(20,-34.3,25)').replace('头部线束鞍及22mm','头部线束鞍（底面99.5mm，高于法兰）及22mm')
 p.write_text(s,encoding='utf8')
print('BOARDS_AND_BLANK_TABLES_COMPLETE')
