"""Optional review contact sheet; requires Pillow and a CJK font."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import argparse
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--font',type=Path)
args=parser.parse_args()
candidates=[args.font,Path('C:/Windows/Fonts/msyh.ttc'),Path('/System/Library/Fonts/PingFang.ttc'),Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
fontfile=next((p for p in candidates if p and p.is_file()),None)
if fontfile is None:raise FileNotFoundError('Provide a Chinese font with --font /path/to/font.ttf')
font=ImageFont.truetype(str(fontfile),30);small=ImageFont.truetype(str(fontfile),23)
out=Image.new('RGB',(1800,730),'#efefef');d=ImageDraw.Draw(out)
d.text((32,20),'EffMeet2  圆润转头版 · 建模姿态预览',fill='#25272a',font=font)
for i,(name,label) in enumerate([('left','左转 45°'),('center','正向'),('right','右转 45°')]):
    im=Image.open(ROOT/'renders'/'review-02'/('07_yaw_'+name+'.png')).convert('RGB');im.thumbnail((580,560))
    out.paste(im,(i*600+(600-im.width)//2,70));d.text((i*600+30,625),label,fill='#25272a',font=font)
d.text((32,685),'固定底座不动；模型仅验证姿态与部分几何间隙，线束、驱动及承重仍需实测。',fill='#555b60',font=small)
local=ROOT/'local-only';local.mkdir(exist_ok=True)
out.save(local/'EffMeet2_圆润转头版_三姿态预览_重建.png')
