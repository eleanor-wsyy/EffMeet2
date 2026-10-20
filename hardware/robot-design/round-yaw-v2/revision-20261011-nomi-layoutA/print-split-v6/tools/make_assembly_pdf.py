"""从 ASSEMBLY.md 生成可打印 PDF 安装手册（v4 风格：藏青/青绿/图鉴表/页脚），Edge 无头打印 + pymupdf 盖页脚。
用法: python tools/make_assembly_pdf.py   # 输出 EffMeet2-安装手册v5-<日期>.pdf 于 print-split-v6/
"""
import os,subprocess,datetime
from pathlib import Path
import markdown

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'ASSEMBLY.md'
OUTDIR=ROOT
EDGE=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if not Path(EDGE).exists():EDGE=r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
FOOTER_LEFT='EffMeet2 v6 · 安装手册 v5 · 2026-10-20'

md=markdown.Markdown(extensions=['tables','fenced_code','sane_lists'])
body=md.convert(SRC.read_text(encoding='utf8'))
# 修正框（首个 blockquote）染色：v4 风格浅青底
body=body.replace('<blockquote>','<blockquote class="fixbox">',1)
css='''
@page{size:A4;margin:14mm 12mm 16mm}
body{font-family:"Microsoft YaHei","SimHei",sans-serif;font-size:9.8px;line-height:1.5;color:#333;margin:0}
h1{font-family:"Microsoft YaHei";font-size:17px;font-weight:700;color:#1a3a4a;margin:0 0 8px;line-height:1.35}
blockquote.fixbox{background:#e8f4f0;border-radius:6px;padding:8px 12px;margin:0 0 12px;font-size:9px;line-height:1.55;color:#1a3a4a}
blockquote.fixbox p{margin:2px 0}
h2{font-family:"Microsoft YaHei";font-size:13.5px;font-weight:700;color:#1a3a4a;margin:14px 0 2px;padding:0}
h3{font-family:"Microsoft YaHei";font-size:11px;font-weight:700;color:#0e7c7b;margin:10px 0 4px}
h2 + p, h2 + blockquote{color:#0e7c7b;font-weight:700}
table{border-collapse:collapse;width:100%;margin:5px 0 10px;font-size:8.6px;line-height:1.45}
th{background:#1a3a4a;color:#fff;font-weight:600;padding:4px 5px;border:1px solid #1a3a4a;text-align:left}
td{border:1px solid #c9d2d6;padding:3.5px 5px;vertical-align:middle}
tr:nth-child(even) td{background:#f5f7fa}
td img{width:46px;height:46px;object-fit:contain;background:#f5f7fa;border-radius:4px;display:block}
strong{color:#111;font-weight:700}
code{background:#f1f3f5;padding:0 3px;border-radius:3px;font-family:Consolas,monospace;font-size:8.6px}
a{color:#0e7c7b;text-decoration:none}
hr{border:0;border-top:1px solid #ddd;margin:10px 0}
ul,ol{margin:3px 0 8px 16px;padding:0}
li{margin:1.5px 0}
blockquote{margin:6px 0;padding:4px 10px;border-left:3px solid #b85237;background:#fff8ec}
p{margin:3px 0}
'''
html=f'<!doctype html><meta charset="utf-8"><style>{css}</style><body>{body}</body>'
html_path=ROOT/'_assembly_v5.html'
html_path.write_text(html,encoding='utf8')
date=datetime.date.today().strftime('%Y%m%d')
raw=ROOT/f'_assembly_v5_raw.pdf'
out=ROOT/f'EffMeet2-安装手册v5-{date}.pdf'
cmd=[EDGE,'--headless','--disable-gpu',f'--print-to-pdf={raw}','--no-pdf-header-footer',
     '--run-all-compositor-stages-before-draw','--virtual-time-budget=8000',f'file://{html_path}']
r=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
html_path.unlink(missing_ok=True)
assert raw.exists(),(r.returncode,r.stderr[-300:] if r.stderr else '')
# 页脚：左 手册名·日期，右 第 N 页（v4 风格）
import fitz
doc=fitz.open(raw)
for i,page in enumerate(doc):
    w,h=page.rect.width,page.rect.height
    page.insert_text((36,h-22),FOOTER_LEFT,fontsize=7.2,fontname='china-s',color=(0.45,0.45,0.45))
    t=f'第 {i+1} 页'
    tw=fitz.get_text_length(t,fontname='china-s',fontsize=7.2)
    page.insert_text((w-36-tw,h-22),t,fontsize=7.2,fontname='china-s',color=(0.45,0.45,0.45))
doc.save(out);doc.close();raw.unlink(missing_ok=True)
print('PDF:',out,'pages=',fitz.open(out).page_count,'size=',out.stat().st_size)
