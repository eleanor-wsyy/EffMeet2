"""Compose review boards from real Blender renders, not generative redraws."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
ROOT=Path(__file__).resolve().parent
R=ROOT/'renders'/'review-05';OUT=ROOT/'drawings';OUT.mkdir(exist_ok=True)
FONT=Path('C:/Windows/Fonts/msyh.ttc');BOLD=Path('C:/Windows/Fonts/msyhbd.ttc')
INK='#20272c';MUTE='#646c71';PAPER='#f4f3ef';LINE='#b4b7b6';ACCENT='#b56c42'
def f(s,b=False):return ImageFont.truetype(str(BOLD if b else FONT),s)
def text(d,p,s,size=23,b=False,c=INK):d.text(p,s,font=f(size,b),fill=c)
def board(title,subtitle,size=(1800,1200)):
 im=Image.new('RGB',size,PAPER);d=ImageDraw.Draw(im);text(d,(55,45),title,47,True);text(d,(58,111),subtitle,23,c=MUTE);d.line((55,157,size[0]-55,157),fill=LINE,width=2);return im,d

def place(im,name,box):
 src=Image.open(R/name).convert('RGB');src=src.resize((box[2],box[3]),Image.Resampling.LANCZOS);im.paste(src,box[:2])
def lines(d,x,y,items,size=23,step=36,c=INK):
 for n,line in enumerate(items):text(d,(x,y+n*step),line,size,c=c)
def arrow(d,a,b,label,offset=(0,0)):
 d.line((*a,*b),fill=ACCENT,width=2)
 dx=b[0]-a[0];dy=b[1]-a[1];ll=(dx*dx+dy*dy)**.5;ux=dx/ll;uy=dy/ll
 for p,s in [(a,1),(b,-1)]:
  q=(p[0]+s*ux*11,p[1]+s*uy*11);d.polygon([p,(q[0]-uy*4,q[1]+ux*4),(q[0]+uy*4,q[1]-ux*4)],fill=ACCENT)
 text(d,((a[0]+b[0])/2+offset[0],(a[1]+b[1])/2+offset[1]),label,21,True,c=ACCENT)
#01: hero and restrained CMF / honest interface notes.
im,d=board('EffMeet2 / NOMI · 布局 A','v4工程候选 · 实际Blender模型渲染 · 尚未制造／实机放行')
place(im,'01_hero.png',(55,190,1100,825))
x=1200;text(d,(x,197),'圆头，圆脸，短连接',28,True)
lines(d,x,250,['近球形头壳＋Ø106黑圆脸','矩形LCD自带屏面露出','暖白双眼；不加嘴／文字','前肩小按钮，四条真实声槽'],22,35)
text(d,(x,418),'新版硬件，固定拾音',27,True)
lines(d,x,470,['GOOUU核心板固定在后部','头内只装LCD＋相机','双INMP441／电源／舵机固定','±45°，真实间隔14mm'],22,35)
text(d,(x,635),'CMF / 裸打哑光',27,True)
d.ellipse((x,690,x+56,746),fill='#949799');d.ellipse((x+85,690,x+141,746),fill='#22272b');text(d,(x+168,700),'灰 / 黑 PLA Matte',23)
lines(d,x,775,['不喷漆、不加透明玻璃罩','细层纹／颜色以正式样片为准','图中材质是中性设计预览'],21,34,c=MUTE)
text(d,(x,920),'180 × 164 × 222 mm',28,True)
text(d,(55,1060),'保留 NOMI 的温和表情与圆润比例，把开孔、电子容量和转轴间隙留在真实模型中。',27,True)
text(d,(55,1120),'本轮没有实机功能PASS；实物配合、轴承固定、FPC寿命和固件需按新版指南验收。',22,c=MUTE)
im.save(OUT/'01_主视觉_CMF.png',optimize=True)
#02: actual orthographic review frames, dimension annotation in mm. Not manufacturing drawing.
im,d=board('三视图 / 名义尺寸','同一模型、同一修订 · 单位 mm · 包络与接口审阅，不是施工／加工图')
for name,x,title in [('02_front.png',55,'正面'),('03_side.png',625,'侧面'),('04_top.png',1195,'顶部')]:
 place(im,name,(x,220,550,413));text(d,(x,178),title,25,True)
# Blender ortho scale335 applies to landscape width; sheet image widths are550.
s=550/335;cx=55+275;cy=220+206.5;bottom=cy+111*s;top=cy-(222-111)*s
arrow(d,(45,bottom),(45,top),'222',(-31,-15));arrow(d,(cx-90*s,665),(cx+90*s,665),'180',(-25,5))
sx=625+275;arrow(d,(sx-82*s,665),(sx+82*s,665),'164',(-25,5))
st=550/280;tx=1195+275;ty=220+206.5;arrow(d,(tx-90*st,665),(tx+90*st,665),'180',(-25,5));arrow(d,(1758,ty-82*st),(1758,ty+82*st),'164',(-40,-15))
text(d,(55,745),'轮廓与关键接口',29,True)
lines(d,55,800,['整机：180W × 164D × 222H；底座壳体76高＋2mm现成硅胶脚垫。','头部母体：150 × 128 × 144；Z92截底后实际头壳占位高约130。','圆脸：Ø106；矩形贯通窗58.2 × 43.8；屏有效区57.6 × 43.2为预算。','短颈：外露Ø46；盖孔Ø48；Ø22跨轴通道；头壳至底座14真实间隙。','头底接收面3.2厚；隐藏Ø62法兰与两处M3候选孔；具体公差／螺母／长度待样件。'],23,43)
text(d,(55,1068),'实板、屏厚、镜头、FPC出口与支架孔位未实测。图中开孔和名义包络不等于全件可装配。',21,c=MUTE)
text(d,(55,1120),'已下单套装扩展板未测，不纳入容纳结论；屏／外接音频尺寸需到货回填。',22,c=MUTE)
im.save(OUT/'02_三视图_名义尺寸.png',optimize=True)
#03: explosion and internal layout, clearly separate manufactured geometry from proxies.
im,d=board('分解与内舱 / 实际模型','真实场景分件位移 · 电子件／夹持座／带轮是封装代理 · 不是制造装配爆炸图')
place(im,'09_exploded_layout.png',(55,220,830,623));place(im,'08_internal_layout.png',(915,220,830,623))
text(d,(55,178),'外观件与头部接口分离',25,True);text(d,(915,178),'隐藏外壳后的安装舱',25,True)
lines(d,55,890,['① 圆脸向前移出，头部向上分离；上盖单独拆开。','② 头壳／面板／颈／上盖／杯体保留独立制造边界。','③ 电子件、轴承座、轮／带是名义占位，不照图下单打印。'],22,37)
lines(d,915,890,['④ 后部GOOUU＋双麦；前右功放；后左充电；前扬声器。','⑤ 两只6806承头重，侧置舵机只出转向力。','⑥ 显示线束＋摄像FPC走Ø22通道；具体活动路线必须实测。'],22,37)
text(d,(55,1050),'待锁定：支架／分体轴承座固定／轴向锁定／齿形／舵盘／滑盖导向／公差／两路活动线。',23,True)
text(d,(55,1115),'装配时序：裸板 → 配合样片 → 固定底座 → 支撑与传动 → 显示线束／摄像FPC → 屏／相机 → 封头 → 全项测试。',21,c=MUTE)
im.save(OUT/'03_分解与内舱布局.png',optimize=True)
print(json.dumps({'boards':3,'source':'Blender review-05','actual_pixels':[1800,1200],'manufacturing_release':False},ensure_ascii=False))
