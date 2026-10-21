"""Rebuild the three standalone showcase pages under dist/local/.

Brand system is sourced from the supplied effmeetbot logo:
navy #0A0B27, signal blue #2857F3, warm paper #F7F6F2.
"""
from __future__ import annotations

import base64
import io
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "showcase"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0a0b27"
BLUE = "#2857f3"
PAPER = "#f7f6f2"
GREY = "#6b6b66"


def data_uri(path: Path, max_width: int | None = None, quality: int = 84, fmt: str = "WEBP") -> str:
    image = Image.open(path)
    if fmt == "WEBP":
        image = image.convert("RGB") if image.mode not in ("RGB", "RGBA") else image
        if max_width and image.width > max_width:
            ratio = max_width / image.width
            image = image.resize((max_width, int(image.height * ratio)), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, "WEBP", quality=quality, method=6)
        mime = "image/webp"
    else:
        buffer = io.BytesIO()
        image.save(buffer, "PNG", optimize=True)
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


LOGO = data_uri(ROOT / "assets/brand/effmeetbot-logo.png", fmt="PNG")
ISGBA = (Path.home() / ".kimi-code/sessions/wd_effmeet2_d06e10e404c2/session_26620694-5391-4f97-8e59-9911fb6b9f6d/attachments/f_b69062d8-a226-4875-a706-b48e1e4606a9-GAFA-ISGBA-logo.svg").read_text(encoding="utf-8")
ISGBA = ISGBA.replace("<svg ", '<svg class="isgba" aria-label="ISGBA 广州美术学院湾区创新学院" ', 1)

IMG = {
    "hero": data_uri(ROOT / "site/assets/img/hero.png", max_width=1640, quality=86),
    "front": data_uri(ROOT / "site/assets/img/front.png", max_width=1056, quality=86),
    "side": data_uri(ROOT / "site/assets/img/side.png", max_width=966, quality=86),
    "top": data_uri(ROOT / "site/assets/img/top.png", max_width=1252, quality=86),
    "internal": data_uri(ROOT / "site/assets/img/internal.png", max_width=1800, quality=86),
    "screen_live": data_uri(ROOT / "site/assets/img/screens/screen-live.png", max_width=780, quality=82),
    "screen_confirm": data_uri(ROOT / "site/assets/img/screens/screen-confirm.png", max_width=780, quality=82),
    "screen_map": data_uri(ROOT / "site/assets/img/screens/screen-map.png", max_width=780, quality=82),
    "ai": data_uri(ROOT / "assets/brand/ai-result.png", max_width=1280, quality=84),
}

SCREENS = {
    "01-home": data_uri(ROOT / "dist/review/screens/01-home.png", max_width=780, quality=82),
    "02-join": data_uri(ROOT / "dist/review/screens/02-join.png", max_width=780, quality=82),
    "03-meeting": data_uri(ROOT / "dist/review/screens/03-meeting.png", max_width=780, quality=82),
    "04-candidate": data_uri(ROOT / "dist/review/screens/04-candidate.png", max_width=780, quality=82),
    "05-confirmed": data_uri(ROOT / "dist/review/screens/05-confirmed.png", max_width=780, quality=82),
    "06-map": data_uri(ROOT / "dist/review/screens/06-map.png", max_width=780, quality=82),
    "07-evidence": data_uri(ROOT / "dist/review/screens/07-evidence.png", max_width=780, quality=82),
    "09-history": data_uri(ROOT / "dist/review/screens/09-history.png", max_width=780, quality=82),
    "11-profile": data_uri(ROOT / "dist/review/screens/11-profile.png", max_width=780, quality=82),
    "12-settings": data_uri(ROOT / "dist/review/screens/12-settings.png", max_width=780, quality=82),
    "13-refused": data_uri(ROOT / "dist/review/screens/13-refused.png", max_width=780, quality=82),
    "14-expired": data_uri(ROOT / "dist/review/screens/14-expired.png", max_width=780, quality=82),
}

font_bytes = (ROOT / "site/assets/fonts/inter-var.woff2").read_bytes()
FONT = "data:font/woff2;base64," + base64.b64encode(font_bytes).decode("ascii")

DEMO_URL = "https://codyning-effmeetbot.ms.show/demo/"
SITE_URL = "https://codyning-effmeetbot.ms.show/"
AI_URL = "https://www.modelscope.cn/studios/CodyNing/effmeetbot-ai"
STUDIO_URL = "https://www.modelscope.cn/studios/CodyNing/effmeetbot"
PDF_URL = "https://codyning-effmeetbot.ms.show/docs/EffMeet2_论文依据与技术路径.pdf"


# ---------------------------------------------------------------- official page
def build_official() -> str:
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    css = (ROOT / "site/assets/css/site.css").read_text(encoding="utf-8")
    js = (ROOT / "site/assets/js/site.js").read_text(encoding="utf-8")
    css = css.replace('url("../fonts/inter-var.woff2")', f'url("{FONT}")')
    css += """
/* ---- effmeetbot brand layer ---- */
:root{--navy:#0a0b27;--blue:#2857f3;--blue-soft:rgba(40,87,243,.10);--orange:#2857f3;--orange-soft:rgba(40,87,243,.10);--dark:#0a0b27;--ink:#0a0b27;--ink-soft:#2b2f45;--line:rgba(10,11,39,.14);--line-strong:rgba(10,11,39,.30)}
.btn-solid{background:var(--blue);border-color:var(--blue);color:#fff}
.btn-solid:hover{background:var(--navy);border-color:var(--navy)}
.btn-ghost{border-color:var(--navy);color:var(--navy)}
.btn-ghost:hover{background:var(--navy);color:var(--paper)}
.topbar-cta{border-color:var(--navy)}
.topbar-cta:hover{background:var(--blue);border-color:var(--blue)}
.eyebrow-dot{background:var(--blue)}
.step-no,.principle-no,.num{color:var(--blue);background:none}
.status-partial{color:var(--blue);border-color:rgba(40,87,243,.32)}
.flow-node--accent{background:var(--blue);border-color:var(--blue)}
.entry--ai:hover{background:var(--blue)}
.entry:hover{background:var(--navy)}
.footer{background:var(--navy)}
.hero-figure::before{background:radial-gradient(closest-side,rgba(40,87,243,.09),rgba(40,87,243,0))}
.brand-lockup{display:flex;align-items:center;gap:13px}
.brand-lockup img{height:19px;width:auto;display:block}
.brand-lockup .cn{font-size:21px;font-weight:650;letter-spacing:.06em;white-space:nowrap}
.hero-action-note{margin-top:14px;font-size:11px;line-height:1.7;color:var(--grey-2);max-width:34em}
.value-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:clamp(24px,3vw,48px)}
.value-item{padding-top:18px;border-top:1px solid var(--line-strong)}
.value-item .mono{display:block;margin-bottom:16px;color:var(--blue)}
.value-item h3{font-size:clamp(22px,2vw,28px);font-weight:600;letter-spacing:-.02em;margin-bottom:10px}
.value-item p{font-size:14px;line-height:1.8;color:var(--grey)}
.value-item .status-chip{margin-top:18px}
.embodied{margin-top:clamp(30px,4vw,48px);padding-top:22px;border-top:1px solid var(--line-strong)}
.embodied-head{display:flex;align-items:baseline;justify-content:space-between;gap:20px;margin-bottom:22px}
.embodied-head h3{font-size:clamp(20px,2vw,26px);font-weight:600;letter-spacing:-.01em}
.embodied-flow{list-style:none;display:grid;grid-template-columns:repeat(7,1fr);gap:0;margin:0 0 16px;padding:0;border-top:1px solid var(--line)}
.embodied-flow li{position:relative;padding:14px 12px 12px 0;font-size:12px;color:var(--grey);border-right:1px solid var(--line)}
.embodied-flow li:last-child{border-right:none}
.embodied-flow b{display:block;font-family:var(--font-mono);font-size:9px;font-weight:400;color:var(--blue);margin-bottom:6px}
.embodied-note{font-size:11.5px;line-height:1.8;color:var(--grey-2);max-width:62em}
.logo-plate{display:inline-flex;align-items:center;gap:10px;background:var(--paper);padding:8px 11px}
.logo-plate img{height:16px;width:auto}
.logo-plate .cn{font-size:16px;font-weight:650;letter-spacing:.06em;color:var(--navy)}
.isgba-plate{display:flex;align-items:center;gap:12px;background:var(--paper);padding:10px 14px;margin-top:16px;width:fit-content}
.isgba-plate svg{height:20px;width:auto;display:block}
.isgba-plate span{font-size:10.5px;line-height:1.5;color:var(--grey)}
.footer-brand .footer-fine{margin-top:10px}
.snapshot-note{margin-top:10px;font-family:var(--font-mono);font-size:9.5px;letter-spacing:.06em;color:rgba(247,246,242,.38)}
@media(max-width:900px){.value-grid{grid-template-columns:1fr}.embodied-flow{grid-template-columns:1fr 1fr}.embodied-flow li:nth-child(2n){border-right:none}.embodied-head{display:block}}
@media(max-width:560px){.brand-lockup img{height:16px}.brand-lockup .cn{font-size:18px}}
"""
    assert '<link rel="stylesheet" href="assets/css/site.css">' in html
    html = html.replace('<link rel="stylesheet" href="assets/css/site.css">', f"<style>{css}</style>")

    lockup_old = """    <a class="lockup" href="#top" aria-label="在议 effmeetbot 首页">
      <span class="lockup-cn">在议</span>
      <span class="lockup-rule" aria-hidden="true"></span>
      <span class="wordmark">effmeetbot<span class="wordmark-dots" aria-hidden="true"><i></i><i></i></span></span>
    </a>"""
    lockup_new = f"""    <a class="brand-lockup" href="#top" aria-label="在议 effmeetbot 首页">
      <span class="cn">在议</span>
      <img src="{LOGO}" alt="effmeetbot">
    </a>"""
    assert lockup_old in html
    html = html.replace(lockup_old, lockup_new)
    html = html.replace('<a class="topbar-cta" href="demo/">体验 Demo</a>', f'<a class="topbar-cta" href="{DEMO_URL}" target="_blank" rel="noopener">体验产品</a>')
    html = html.replace('<a href="#problem">问题</a>\n      <a href="#interaction">交互</a>', '<a href="#problem">问题</a>\n      <a href="#values">价值</a>\n      <a href="#interaction">交互</a>')

    actions_old = """        <div class="hero-actions">
          <a class="btn btn-solid" href="demo/">体验产品 <span aria-hidden="true">↗</span></a>
          <a class="btn btn-ghost" href="#design">探索设计 <span aria-hidden="true">↓</span></a>
        </div>"""
    actions_new = f"""        <div class="hero-actions">
          <a class="btn btn-solid" href="{DEMO_URL}" target="_blank" rel="noopener">体验产品交互 <span aria-hidden="true">↗</span></a>
          <a class="btn btn-ghost" href="{AI_URL}" target="_blank" rel="noopener">体验真实 AI 判断 <span aria-hidden="true">↗</span></a>
        </div>
        <p class="hero-action-note">产品交互版是静态模拟环境；AI 判断实验台调用真实 qwen-plus。两者都不是整机实测。</p>"""
    assert actions_old in html
    html = html.replace(actions_old, actions_new)

    values = f"""
  <!-- 03 VALUES -->
  <section class="section" id="values">
    <div class="wrap">
      <header class="section-head section-head--wide">
        <span class="section-index mono">03 / 三个价值</span>
        <h2 class="display">不只是一句<br>被忽略的提醒</h2>
        <p class="head-lede">信息可及、有效参与、协作追溯，是同一套会议协作能力的三个面。</p>
      </header>
      <div class="value-grid">
        <article class="value-item">
          <span class="mono">01 / 信息可及</span>
          <h3>看见现场</h3>
          <p>白板、草图、摊开的图纸，随手一拍，原图直达远程成员手机。远程成员不必靠口头描述想象现场。</p>
          <span class="status-chip status-ok">功能版已实现 · Demo 展示</span>
        </article>
        <article class="value-item">
          <span class="mono">02 / 有效参与</span>
          <h3>让观点被回应</h3>
          <p>AI 发现可能被遗漏的线上观点，先私下询问本人；本人确认后，机器人才转向现场，复述原话要点。</p>
          <span class="status-chip status-partial">软件门控已实现 · 实机联动集成中</span>
        </article>
        <article class="value-item">
          <span class="mono">03 / 协作追溯</span>
          <h3>会后回到原话</h3>
          <p>观点地图关联议题、回应状态与原始发言；每条提醒都能点回当时的证据，而不是一句转述。</p>
          <span class="status-chip status-ok">已实现</span>
        </article>
      </div>
    </div>
  </section>

  <!-- 04 INTERACTION -->"""
    assert "  <!-- 03 INTERACTION -->" in html
    html = html.replace("  <!-- 03 INTERACTION -->", values, 1)

    embodied = f"""
      <div class="embodied">
        <div class="embodied-head">
          <h3>不是播报终端，是一次具身提醒</h3>
          <span class="mono">目标交互 / EMBODIED</span>
        </div>
        <ol class="embodied-flow">
          <li><b>01</b>私人候选</li>
          <li><b>02</b>本人确认</li>
          <li><b>03</b>适当时机</li>
          <li><b>04</b>转头 orient</li>
          <li><b>05</b>状态灯 light</li>
          <li><b>06</b>语音提醒 speak</li>
          <li><b>07</b>回应与追溯</li>
        </ol>
        <p class="embodied-note">已实现：本人确认与服务端门控；<code>orient</code> / <code>light</code> / <code>speak</code> / <code>stop</code> 已有设备命令。集成中：转头、状态灯与实声的完整自动联动。未验收：整机连续会议实机闭环。播报动作为目标效果，当前以模拟回执演示。</p>
      </div>
    </div>
  </section>

  <!-- 05 DESIGN -->"""
    tail_old = """      </div>
    </div>
  </section>

  <!-- 04 DESIGN -->"""
    assert tail_old in html
    html = html.replace(tail_old, embodied, 1)

    for old, new in [("03 / 交互", "04 / 交互"), ("04 / 工业设计", "05 / 工业设计"), ("05 / 边界", "06 / 边界"), ("06 / 技术", "07 / 技术"), ("07 / 体验", "08 / 体验")]:
        html = html.replace(old, new)

    # swap public links in resources / entries
    html = html.replace('<a class="entry" href="demo/">', f'<a class="entry" href="{DEMO_URL}" target="_blank" rel="noopener">')
    html = html.replace(f'<a class="entry entry--ai" href="{AI_URL}" target="_blank" rel="noopener" id="ai-demo-link">', f'<a class="entry entry--ai" href="{AI_URL}" target="_blank" rel="noopener" id="ai-demo-link">')
    html = html.replace('href="docs/EffMeet2_论文依据与技术路径.pdf"', f'href="{PDF_URL}"')
    html = html.replace('href="assets/film/effmeetbot-film-1080p.mp4"', f'href="{SITE_URL}assets/film/effmeetbot-film-1080p.mp4"')
    html = html.replace('<a href="demo/">产品 Demo</a>', f'<a href="{DEMO_URL}" target="_blank" rel="noopener">产品 Demo</a>')

    # footer brand
    footer_old = """    <div class="footer-brand">
      <span class="lockup-cn">在议</span>
      <span class="wordmark">effmeetbot<span class="wordmark-dots" aria-hidden="true"><i></i><i></i></span></span>
      <p>在线，不等于在场。</p>
    </div>"""
    footer_new = f"""    <div class="footer-brand">
      <div class="logo-plate"><img src="{LOGO}" alt="effmeetbot"><span class="cn">在议</span></div>
      <p>在线，不等于在场。</p>
      <div class="isgba-plate">{ISGBA}<span>广州美术学院 湾区创新学院（ISGBA）<br>团队所属机构署名</span></div>
      <p class="footer-fine">机构标识仅用于团队署名，不代表学校主办、认证或联合研发。</p>
      <p class="snapshot-note">本页为本地展示快照 · 在线应用以链接为准</p>
    </div>"""
    assert footer_old in html
    html = html.replace(footer_old, footer_new)

    # images to data URIs
    mapping = {
        "assets/img/hero.png": IMG["hero"],
        "assets/img/front.png": IMG["front"],
        "assets/img/side.png": IMG["side"],
        "assets/img/top.png": IMG["top"],
        "assets/img/internal.png": IMG["internal"],
        "assets/img/screens/screen-live.png": IMG["screen_live"],
        "assets/img/screens/screen-confirm.png": IMG["screen_confirm"],
        "assets/img/screens/screen-map.png": IMG["screen_map"],
        "assets/img/ai-demo.png": IMG["ai"],
    }
    for old, uri in mapping.items():
        html = html.replace(f'src="{old}"', f'src="{uri}"')

    html = html.replace('<script src="assets/js/site.js"></script>', f"<script>{js}</script>")
    html = html.replace('<link rel="preload" href="assets/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin>', "")
    html = html.replace("EffMeet 2", "在议")
    (OUT / "在议-官网.html").write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------- AI snapshot
def build_ai() -> str:
    card = """
      <article class="result {cls}">
        <div class="result-head"><span class="tag">{tag}</span><span class="state">{state}</span></div>
        <h3>{title}</h3>
        <p class="reason">{reason}</p>
        <dl><div><dt>证据</dt><dd>{ev}</dd></div><div><dt>耗时</dt><dd>{ms}</dd></div><div><dt>Claim</dt><dd class="mono">{cid}</dd></div></dl>
      </article>"""
    cards = "".join(card.format(**item) for item in [
        dict(cls="uncertain", tag="A / 潜在遗漏测试", state="uncertain · 模型实际弃权", title="模型没有把它判成“可能未回应”",
             reason="线上成员丙提出用重量传感器做满溢检测，但后续现场发言只讨论折叠结构与开模成本，模型无法确认语义指向，选择弃权。", ev="8 条", ms="5.5 s", cid="f8dc7f03"),
        dict(cls="responded", tag="B / 已回应", state="responded", title="现场明确承接了观点",
             reason="现场甲在观点之后明确肯定重量传感器方案，乙进一步呼应；时间邻近且语义直接指向该观点。", ev="8 条", ms="7.6 s", cid="884bb65e"),
        dict(cls="uncertain", tag="C / 不确定", state="uncertain", title="转写破碎，无法判断回应关系",
             reason="多人抢话、语句不完整，现场发言围绕线头松动与信号恢复，无法确认是否回应了传感器问题。", ev="7 条", ms="7.3 s", cid="cb023ba3"),
    ])
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>在议·effmeetbot｜AI 判断实验台 · 真实结果快照</title>
<style>
:root{{--navy:{NAVY};--blue:{BLUE};--paper:{PAPER};--grey:{GREY};--line:rgba(10,11,39,.14)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--navy);font-family:"Inter","PingFang SC","HarmonyOS Sans SC","Microsoft YaHei",sans-serif;line-height:1.75}}
img{{max-width:100%;display:block}}
a{{color:inherit;text-decoration:none}}
.wrap{{max-width:1200px;margin:0 auto;padding:0 clamp(20px,4vw,56px)}}
header{{border-bottom:1px solid var(--line)}}
.bar{{display:flex;align-items:center;gap:18px;padding:20px 0}}
.brand{{display:flex;align-items:center;gap:12px;white-space:nowrap}}
.brand img{{height:20px;width:auto}}
.brand b{{font-size:19px;letter-spacing:.06em}}
.bar .right{{margin-left:auto;display:flex;gap:18px;font-size:13px;color:var(--grey)}}
.bar .right a:hover{{color:var(--blue)}}
.hero{{padding:56px 0 28px;display:grid;grid-template-columns:1.6fr 1fr;gap:40px;align-items:end}}
h1{{font-size:clamp(40px,6vw,78px);line-height:1.02;letter-spacing:-.04em;margin:0}}
.hero p{{margin:16px 0 0;color:var(--grey);max-width:34em}}
.meta{{border-top:1px solid var(--line);font-size:12px}}
.meta div{{display:flex;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid var(--line);color:var(--grey)}}
.meta dt{{font-family:Consolas,monospace;font-size:10px;color:#93938c;letter-spacing:.1em}}
.banner{{margin:10px 0 34px;padding:18px 22px;background:rgba(40,87,243,.08);border-left:3px solid var(--blue);display:flex;align-items:center;gap:18px;justify-content:space-between;flex-wrap:wrap}}
.banner p{{margin:0;font-size:13px;color:var(--navy)}}
.btn{{display:inline-flex;align-items:center;gap:8px;background:var(--blue);color:#fff;padding:11px 20px;border-radius:100px;font-size:13px}}
.btn:hover{{background:var(--navy)}}
section{{padding:34px 0}}
.results{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.result{{border-top:2px solid var(--navy);background:#fff;padding:20px;display:flex;flex-direction:column}}
.result.responded{{border-top-color:#2f6b45}}
.result.uncertain{{border-top-color:#93938c}}
.result-head{{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:10px}}
.tag{{font-family:Consolas,monospace;color:var(--grey);letter-spacing:.08em}}
.state{{padding:3px 9px;border:1px solid var(--line);border-radius:100px;color:var(--grey);white-space:nowrap}}
.responded .state{{color:#2f6b45;border-color:rgba(47,107,69,.3)}}
.uncertain .state{{color:#6b6b66}}
.result h3{{font-size:17px;margin:16px 0 8px;line-height:1.4}}
.reason{{font-size:12.5px;color:var(--grey);margin:0 0 18px;flex:1}}
.result dl{{margin:0;border-top:1px solid var(--line);padding-top:10px;font-size:11px}}
.result dl div{{display:flex;justify-content:space-between;gap:10px;padding:4px 0;color:var(--grey)}}
.result dt{{font-family:Consolas,monospace;font-size:9px;letter-spacing:.1em;color:#93938c}}
.mono{{font-family:Consolas,monospace;font-size:10px}}
.why{{display:grid;grid-template-columns:1fr 2fr;gap:32px;padding:28px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
.why h2{{font-size:22px;margin:0;line-height:1.3}}
.why p{{margin:0;font-size:14px;color:var(--grey)}}
figure{{margin:34px 0 0}}
figure img{{border:1px solid var(--line);background:#fff}}
figcaption{{font-size:11px;color:#93938c;margin-top:10px}}
footer{{margin-top:50px;border-top:1px solid var(--line);padding:26px 0 50px;font-size:11px;color:#93938c;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr}}.results{{grid-template-columns:1fr}}.why{{grid-template-columns:1fr}}.bar{{flex-wrap:wrap;gap:10px}}.bar .right{{margin-left:0;gap:14px}}}}
</style></head><body>
<header><div class="wrap bar">
  <a class="brand" href="在议-官网.html"><b>在议</b><img src="{LOGO}" alt="effmeetbot"></a>
  <div class="right"><a href="在议-官网.html">返回产品官网</a><a href="{AI_URL}" target="_blank" rel="noopener">在线实验台 ↗</a></div>
</div></header>
<main class="wrap">
  <div class="hero">
    <div><h1>AI 判断实验台<br>真实结果快照</h1><p>本页记录 2026-10-21 的真实 <code>qwen-plus</code> 运行结果，不是可交互界面，也不支持在页内调用 API。</p></div>
    <dl class="meta"><div><dt>模型</dt><dd>qwen-plus · DashScope</dd></div><div><dt>校验</dt><dd>AnalysisResult v1 · 服务端</dd></div><div><dt>记录</dt><dd>3 组 · 公网与本地</dd></div><div><dt>状态</dt><dd>真实调用 · 结果未改写</dd></div></dl>
  </div>
  <div class="banner"><p><strong>本页为真实 AI 运行结果快照。</strong> 交互分析请进入在线实验台；公共 Demo 使用免费 CPU，冷启动可能需要数十秒。</p><a class="btn" href="{AI_URL}" target="_blank" rel="noopener">进入在线实验台 ↗</a></div>
  <section>
    <div class="results">{cards}</div>
  </section>
  <div class="why"><h2>为什么弃权<br>同样重要？</h2><p>证据不足时不强行判断，是避免机器人无依据打断现场的设计机制。系统只判断“是否已有可关联的现场回应”，不评价观点对错；拿不准就输出 uncertain，不生成提醒候选。A 的测试场景名为“潜在遗漏”，但模型实际选择了弃权——这比为了演示效果改成正向结果更接近真实产品。</p></div>
  <figure><img src="{IMG['ai']}" alt="公网 AI 实验台真实运行结果：不确定（uncertain）"><figcaption>公网真实调用 · 2.5 s · 契约校验通过 · 页面显示 uncertain</figcaption></figure>
  <footer><span>在议·effmeetbot / AI 判断实验台</span><span>本页为静态快照，不连接模型 API · <a href="{SITE_URL}" target="_blank" rel="noopener">产品官网 ↗</a></span></footer>
</main></body></html>"""
    (OUT / "在议-AI判断实验台.html").write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------- mobile gallery
def build_mobile() -> str:
    base = (ROOT / "dist/review/mobile-ui.html").read_text(encoding="utf-8")
    base = base.replace("--orange: #e8502d;", f"--blue: {BLUE}; --navy: {NAVY}; --orange: {BLUE};")
    base = base.replace("--ink: #1f201f;", f"--ink: {NAVY};")
    base = base.replace("--line: rgba(31,32,31,.14);", " --line: rgba(10,11,39,.14);")
    base = base.replace(":root {", f":root {{\n    --blue: {BLUE};\n    --navy: {NAVY};")
    # brand header
    old_header = """    <div class="brand"><b>在议</b><span>effmeetbot</span></div>
    <div class="mono">Mobile UI / 2026-10-21</div>
    <a href="http://127.0.0.1:8780/" target="_blank" rel="noopener">打开可交互 Demo ↗</a>"""
    new_header = f"""    <div class="brand"><b>在议</b><img src="{LOGO}" alt="effmeetbot"></div>
    <nav class="chapters" aria-label="界面章节">
      <a href="#core">核心交互</a><a href="#confirm">候选确认</a><a href="#map">观点地图</a><a href="#other">其他界面</a>
    </nav>
    <a href="{DEMO_URL}" target="_blank" rel="noopener">打开可交互 Demo ↗</a>"""
    assert old_header in base
    base = base.replace(old_header, new_header)
    base = base.replace("https://codyning-effmeetbot.ms.show/demo/", DEMO_URL)
    # anchors
    base = base.replace('<section>\n    <div class="sec-head">\n      <h2>主线：从发言到被授权</h2>', '<section id="core">\n    <div class="sec-head">\n      <h2>主线：从发言到被授权</h2>')
    base = base.replace('<article class="card">\n        <div class="card-head"><h3>本人确认</h3><span class="num">04</span></div>', '<article class="card" id="confirm">\n        <div class="card-head"><h3>本人确认</h3><span class="num">04</span></div>')
    base = base.replace('<article class="card">\n        <div class="card-head"><h3>观点地图</h3><span class="num">06</span></div>', '<article class="card" id="map">\n        <div class="card-head"><h3>观点地图</h3><span class="num">06</span></div>')
    base = base.replace('<section>\n    <div class="sec-head">\n      <h2>记录与账户</h2>', '<section id="other">\n    <div class="sec-head">\n      <h2>记录与账户</h2>')
    # images
    for name, uri in SCREENS.items():
        base = base.replace(f'src="screens/{name}.png"', f'src="{uri}"')
    # css additions
    base = base.replace("footer { padding: 32px 0 56px;", """footer { padding: 32px 0 56px;""")
    base = base.replace("</style>", f"""
  .top-inner {{ padding: 22px clamp(20px, 4vw, 64px); }}
  .brand img {{ height: 18px; width: auto; display: block; }}
  .brand b {{ white-space: nowrap; font-size: 18px; }}
  .chapters {{ display: flex; gap: 16px; margin-left: auto; font-size: 11px; color: var(--grey); }}
  .chapters a:hover {{ color: var(--blue); }}
  .chip::before {{ background: var(--blue); }}
  .chip.ok {{ color: #2f6b45; }}
  .chip.ok::before {{ background: #2f6b45; }}
  .num {{ color: var(--blue); }}
  .back {{ font-size: 11px; color: var(--grey); }}
  .chip {{ align-self: flex-start; }}
  @media (max-width: 760px) {{
    .top-inner {{ flex-wrap: wrap; gap: 8px; justify-content: flex-start; }}
    .top-inner > a:last-child {{ margin-left: auto; }}
    .chapters {{ order: 3; flex-basis: 100%; width: 100%; margin-left: 0; gap: 14px; overflow-x: auto; padding-bottom: 2px; }}
    .chapters a {{ white-space: nowrap; }}
    .top a {{ font-size: 11px; }}
    .brand b {{ font-size: 17px; }}
    .brand img {{ height: 16px; }}
  }}
</style>""")
    base = base.replace('<a href="https://www.modelscope.cn/studios/CodyNing/effmeetbot" target="_blank" rel="noopener">打开可交互 Demo ↗</a>',
                        f'<a href="{DEMO_URL}" target="_blank" rel="noopener">打开可交互 Demo ↗</a>')
    base = base.replace('<footer>\n    <span>在议 · effmeetbot / 手机端界面全景</span>',
                        f'<footer>\n    <span>在议 · effmeetbot / 手机端界面全景 · <a class="back" href="在议-官网.html">返回产品官网</a></span>')
    (OUT / "在议-手机端界面全景.html").write_text(base, encoding="utf-8")
    return base


if __name__ == "__main__":
    build_official()
    build_ai()
    build_mobile()
    index = (OUT / "index.html").read_text(encoding="utf-8")
    index = index.replace("#e8502d", BLUE).replace("#1f201f", NAVY)
    (OUT / "index.html").write_text(index, encoding="utf-8")
    print("built", [p.name for p in OUT.glob("*.html")])
