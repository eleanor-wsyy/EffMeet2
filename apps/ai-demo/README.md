# 在议 · effmeetbot — AI 判断实验台

真实调用阿里云百炼 `qwen-plus`，判断一条线上成员的观点是否已经得到现场回应。输出三态与证据 ID，服务端校验后才展示；没有 Key 时明确报错，不返回伪造结果。

## 本地运行

```powershell
.\.venv\Scripts\python.exe -m pip install -r apps/ai-demo/requirements.txt
$env:QWEN_API_KEY = "sk-..."
.\.venv\Scripts\python.exe apps/ai-demo/app.py
# http://127.0.0.1:7860
```

可选环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `QWEN_API_KEY` | 无 | DashScope Key，只在服务端读取 |
| `QWEN_MODEL` | `qwen-plus` | 判断模型 |
| `PORT` | `7860` | 监听端口 |

## 自检（不需要 Key）

```powershell
.\.venv\Scripts\python.exe apps/ai-demo/selftest.py
```

覆盖：三态合法、虚构证据拒绝、responded 无现场证据拒绝、uncertain 带文案拒绝、超长输入拒绝、无 Key 不产生假结果、问句/指令文案拒绝。

## 部署到魔搭创空间（Gradio）

1. 新建 Gradio 创空间，把 `app.py`、`presets.py`、`requirements.txt`、`bundle.json`（可选，用于契约校验回退）放到根目录。
2. 在创空间 **Settings → Secrets** 新增 `QWEN_API_KEY`，不要写进代码或 README。
3. 启动命令使用 `python app.py`，端口读取平台注入的 `PORT`（默认 7860）。
4. 发布后用公开地址替换官网 `index.html` 中 `#ai-demo-link` 的 `href`，并移除“部署中”状态。

## 输入格式

每行一条发言：

```
[现场|线上] 发言者ID(u1): 原文
```

最多 12 条、总字符 ≤ 6000。三组预设只是输入，真实模型结果可能与预设名称不同，界面始终展示真实返回。

## 限制

- 只做文本判断，不接语音 ASR 与机器人。
- 单进程每分钟最多 6 次真实调用。
- 公共 Demo 使用免费 CPU 资源，冷启动与排队可能较慢。
