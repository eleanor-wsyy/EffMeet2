"""Build self-contained local HTML files for offline review.

Outputs to dist/local/:
  - 在议-官网.html
  - 在议-手机端界面全景.html
  - 在议-AI判断实验台.html
  - index.html
"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "local"
WEB = "https://codyning-effmeetbot.ms.show"
AI = "https://www.modelscope.cn/studios/CodyNing/effmeetbot-ai"


def webp(path: Path, max_width: int = 1400, quality: int = 88) -> str:
    image = Image.open(path).convert("RGBA")
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, round(image.height * ratio)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", quality=quality, method=6)
    return "data:image/webp;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def inline_css(css: str) -> str:
    font = ROOT / "site" / "assets" / "fonts" / "inter-var.woff2"
    data = base64.b64encode(font.read_bytes()).decode("ascii")
    return css.replace("../fonts/inter-var.woff2", f"data:font/woff2;base64,{data}")


def build_site() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = inline_css((ROOT / "site" / "assets" / "css" / "site.css").read_text(encoding="utf-8"))
    js = (ROOT / "site" / "assets" / "js" / "site.js").read_text(encoding="utf-8")

    html = re.sub(r'<link rel="stylesheet" href="assets/css/site.css">', f"<style>\n{css}\n</style>", html)
    html = re.sub(r'<script src="assets/js/site.js"></script>', f"<script>\n{js}\n</script>", html)
    html = re.sub(r'<link rel="preload"[^>]*>', "", html)
    html = re.sub(r'<meta property="og:image"[^>]*>', "", html)
    html = html.replace('loading="lazy"', 'loading="eager"')

    for path in sorted((ROOT / "site" / "assets" / "img").rglob("*.png")):
        rel = path.relative_to(ROOT / "site").as_posix()
        max_width = 1600 if path.parent.name == "img" else 700
        html = html.replace(f'src="{rel}"', f'src="{webp(path, max_width)}"')

    favicon = (ROOT / "site" / "assets" / "favicon.svg").read_text(encoding="utf-8")
    html = html.replace('href="assets/favicon.svg"', 'href="data:image/svg+xml;base64,' + base64.b64encode(favicon.encode()).decode() + '"')

    html = html.replace('href="demo/"', f'href="{WEB}/demo/" target="_blank" rel="noopener"')
    html = html.replace('href="docs/EffMeet2_论文依据与技术路径.pdf"', f'href="{WEB}/docs/EffMeet2_论文依据与技术路径.pdf"')
    html = html.replace("<title>", "<title>[本地文件] ")

    (OUT / "在议-官网.html").write_text(html, encoding="utf-8")


def build_mobile() -> None:
    html = (ROOT / "dist" / "review" / "mobile-ui.html").read_text(encoding="utf-8")
    screens = ROOT / "dist" / "review" / "screens"
    for path in sorted(screens.glob("*.png")):
        html = html.replace(f'src="screens/{path.name}"', f'src="{webp(path, 600, 90)}"')
    html = html.replace('href="http://127.0.0.1:8780/"', f'href="{WEB}/demo/"')
    (OUT / "在议-手机端界面全景.html").write_text(html, encoding="utf-8")


def build_ai() -> None:
    shot = ROOT / ".agy-staff" / "shots" / "ai-public-result.png"
    shot_src = webp(shot, 1280, 88) if shot.exists() else ""

    rows = [
        ("A", "可能未回应", "uncertain", "弃权", "2.5 s", "8 条",
         "线上丙提出用重量传感器做满溢检测；后续现场发言均围绕折叠结构，未提及传感器、成本或隐私，模型无法确认语义指向。"),
        ("B", "已回应", "responded", "回应成立", "7.6 s", "8 条",
         "现场甲明确承接「重量传感器确实便宜一半，还不用处理隐私」，乙进一步呼应，回应证据成立。"),
        ("C", "不确定", "uncertain", "弃权", "7.3 s", "7 条",
         "多人抢话、转写破碎，模型无法确认说话人与回应关系，选择弃权。"),
    ]
    cards = "\n".join(
        f"""<article class="result">
  <div class="result-head"><span class="mono">{key} / {name}</span><span class="badge {status}">{status}</span></div>
  <p class="verdict">{verdict} <span class="meta">{ms} · 证据 {evidence}</span></p>
  <p class="reason">{reason}</p>
</article>"""
        for key, name, status, verdict, ms, evidence, reason in rows
    )

    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>[本地文件] 在议 · AI 判断实验台</title>
<style>
:root{{--paper:#f7f6f2;--ink:#1f201f;--grey:#6b6b66;--line:rgba(31,32,31,.14);--orange:#e8502d;
--sans:"Inter","PingFang SC","Microsoft YaHei",sans-serif;--mono:"Cascadia Mono",Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.7}}
.wrap{{max-width:1180px;margin:0 auto;padding:48px 28px 72px}}
.mono{{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#93938c}}
h1{{font-size:clamp(38px,5vw,64px);line-height:1.04;letter-spacing:-.04em;margin:18px 0 14px;font-weight:600}}
.lede{{max-width:40em;color:var(--grey);font-size:15px;margin:0 0 24px}}
.notice{{border:1px solid var(--line);border-left:3px solid var(--orange);padding:14px 18px;font-size:13px;color:var(--grey);background:#fff;margin:24px 0 32px}}
.cta{{display:inline-flex;gap:10px;align-items:center;background:var(--ink);color:#fff;text-decoration:none;padding:12px 22px;border-radius:100px;font-size:14px}}
.cta:hover{{background:var(--orange)}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:32px 0 40px}}
.result{{border-top:1px solid var(--ink);padding-top:14px}}
.result-head{{display:flex;justify-content:space-between;gap:10px;align-items:center}}
.badge{{font-family:var(--mono);font-size:10px;padding:3px 9px;border-radius:100px;border:1px solid var(--line)}}
.badge.responded{{color:#2f6b45;border-color:#2f6b45}}
.badge.uncertain{{color:var(--grey)}}
.verdict{{font-size:18px;font-weight:600;margin:14px 0 8px}}
.meta{{font-family:var(--mono);font-size:10px;color:#93938c;font-weight:400;margin-left:6px}}
.reason{{font-size:13px;color:var(--grey);margin:0}}
figure{{margin:40px 0 0}}figure img{{width:100%;border:1px solid var(--line);border-radius:6px}}
figcaption{{font-size:11px;color:#93938c;margin-top:8px}}
.footer{{margin-top:48px;padding-top:16px;border-top:1px solid var(--line);font-size:11px;color:#93938c;display:flex;justify-content:space-between;gap:16px}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main class="wrap">
<span class="mono">在议 · effmeetbot / AI 判断实验台 / 本地快照</span>
<h1>AI 提出候选，<br>人保留决定权。</h1>
<p class="lede">真实调用 <code>qwen-plus</code>，输出三态结论、证据 ID 与弃权理由。下面是在线实验台的真实运行结果快照；需要交互时点开在线地址。</p>
<div class="notice">这个本地 HTML 只做结果展示，不包含 API Key，也不能直接调用模型。真实调用运行在魔搭创空间的服务端，Key 只存在创空间 Secrets 中。</div>
<a class="cta" href="{AI}" target="_blank" rel="noopener">打开在线实验台 ↗</a>
<div class="grid">{cards}</div>
<figure><img src="{shot_src}" alt="在线实验台真实运行截图"><figcaption>在线实验台真实运行截图 · 预设 A 判为 uncertain · 契约校验通过</figcaption></figure>
<div class="footer"><span>在议 · effmeetbot</span><span>真实结果，未按预设硬编码</span></div>
</main></body></html>"""
    (OUT / "在议-AI判断实验台.html").write_text(html, encoding="utf-8")


def build_index() -> None:
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>在议 · effmeetbot / 本地文件</title>
<style>
body{{margin:0;background:#f7f6f2;color:#1f201f;font-family:"Inter","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.7}}
main{{max-width:860px;margin:0 auto;padding:72px 28px}}
.mono{{font-family:Consolas,monospace;font-size:10px;letter-spacing:.1em;color:#93938c;text-transform:uppercase}}
h1{{font-size:clamp(40px,6vw,72px);line-height:1.02;letter-spacing:-.04em;margin:18px 0 16px}}
p{{color:#6b6b66;max-width:36em}}
a.card{{display:block;border-top:1px solid rgba(31,32,31,.24);padding:22px 0;color:inherit;text-decoration:none}}
a.card:hover h2{{color:#e8502d}}
h2{{margin:0 0 4px;font-size:24px;font-weight:600;transition:color .2s}}
small{{color:#93938c}}
</style></head><body><main>
<span class="mono">在议 · effmeetbot / 本地文件</span>
<h1>三个本地页面</h1>
<p>全部图片、样式与脚本已内嵌，双击即可打开。在线链接需要联网。</p>
<a class="card" href="在议-手机端界面全景.html"><h2>手机端界面全景</h2><small>10 张真实运行截图 · 主线与辅助页面 · 设计观察</small></a>
<a class="card" href="在议-官网.html"><h2>产品官网</h2><small>主视觉、交互叙事、工业设计、技术链路、体验入口</small></a>
<a class="card" href="在议-AI判断实验台.html"><h2>AI 判断实验台</h2><small>真实 qwen-plus 三组结果快照 · 在线入口</small></a>
</main></body></html>"""
    (OUT / "index.html").write_text(html, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_site()
    build_mobile()
    build_ai()
    build_index()
    for path in sorted(OUT.iterdir()):
        print(path.name, f"{path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
