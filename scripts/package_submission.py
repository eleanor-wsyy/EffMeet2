"""Build the offline submission ZIP from the current site and demos."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAMP = "20261021"
NAME = f"在议-effmeetbot-初赛提交-{STAMP}"
OUT = ROOT / "dist" / f"{NAME}.zip"
STAGE = ROOT / "dist" / NAME

README = """# 在议 · effmeetbot — 初赛提交包

在线，不等于在场。

## 打开官网

```bash
python -m http.server 8000 --directory site
# http://127.0.0.1:8000/
```

`site/` 是完整的静态官网，可直接部署到任意静态托管；`site/demo/` 是产品交互 Demo，数据只在本机 localStorage。

## 跑真实 AI 判断

```bash
python -m venv .venv
.venv\\Scripts\\pip install -r apps/ai-demo/requirements.txt
set QWEN_API_KEY=sk-...
.venv\\Scripts\\python apps/ai-demo/app.py
# http://127.0.0.1:7860
```

未配置 Key 时应用会明确报错，不返回伪造结果。自检：`python apps/ai-demo/selftest.py`。

## 边界

- 机器人图为 v6 工程渲染，不是实机照片。
- 界面截图为演示数据；播报动作为目标效果，当前以模拟回执演示。
- 整机装配与连续会议验收进行中。
"""


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    if OUT.exists():
        OUT.unlink()
    STAGE.mkdir(parents=True)

    shutil.copytree(ROOT / "site", STAGE / "site", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "apps" / "web-demo", STAGE / "apps" / "web-demo",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    shutil.copytree(ROOT / "apps" / "ai-demo", STAGE / "apps" / "ai-demo",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (STAGE / "docs").mkdir()
    shutil.copy2(ROOT / "docs" / "product" / "EffMeet2_论文依据与技术路径.html", STAGE / "docs" / "技术路径.html")
    shutil.copy2(ROOT / "dist" / "submission" / "EffMeet2_论文依据与技术路径.pdf", STAGE / "docs" / "技术资料.pdf")
    shutil.copy2(ROOT / "docs" / "product" / "参赛提交文案_2026-10-21.md", STAGE / "docs" / "参赛提交文案.md")
    shutil.copy2(ROOT / "docs" / "handoff" / "2026-10-21-submission-validation.md", STAGE / "docs" / "验证记录.md")
    (STAGE / "README.md").write_text(README, encoding="utf-8")

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in STAGE.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(STAGE.parent))

    total = sum(p.stat().st_size for p in STAGE.rglob("*") if p.is_file())
    print(f"{OUT}  ({total / 1024 / 1024:.1f} MB unpacked)")


if __name__ == "__main__":
    main()
