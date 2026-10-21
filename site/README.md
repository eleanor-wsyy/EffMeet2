---
sdk: static
license: Apache-2.0
---

# 在议 · effmeetbot — 产品官网

**在线，不等于在场。**

这是「在议」的静态产品官网，可直接作为魔搭创空间（ModelScope Studio）的 `static` 应用发布：仓库根目录即本目录，入口为 `index.html`。

## 目录

```
index.html              官网入口
assets/css/site.css     版式与响应式
assets/js/site.js       导航、揭示动画、锚点
assets/img/             机器人渲染、界面截图、OG 封面
assets/fonts/           Inter 可变字体（自托管）
demo/                   产品交互 Demo（纯静态，localStorage）
docs/                   技术资料 PDF
```

## 本地预览

```bash
python -m http.server 8000 --directory site
# http://127.0.0.1:8000/
```

直接双击 `index.html` 也能看，但 `demo/` 里的 PWA 需要 `http/https`。

## 发布到魔搭创空间

1. 在魔搭「创空间 → 创建创空间」选择 **Static**，或新建编程式创空间后把 SDK 设为 `static`。
2. 把本目录全部文件放到创空间仓库根目录（`index.html` 必须在根）。
3. 推送后等待构建，公开地址形如 `https://modelscope.cn/studios/<用户名>/<空间名>`。
4. 把该地址填回 `index.html` 中 `#ai-demo-link` 之外的入口说明，并同步赛事表单。

## 真实性边界

- 机器人图为 v6 工程模型渲染，不是实机照片。
- 界面截图为演示数据。
- 播报动作为目标效果，当前以模拟回执演示。
- 整机装配与连续会议验收进行中；技术页按“已验证 / 分段验证 / 未验收”标注。

## 素材

机器人渲染由仓库内 v6 Blender 模型经 `scripts/render_site_assets.py` 生成；界面截图来自 `apps/web-demo/`。第三方字体 Inter 以 OFL 许可自托管。
