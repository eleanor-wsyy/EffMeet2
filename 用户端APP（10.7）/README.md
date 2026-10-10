# 用户端 APP（10.7）交付入口

此目录保留作为原交付包的入口，不再保存整仓代码副本。**唯一维护源为仓库根目录的 `apps/web/`，配套后端为根目录 `services/`。** 用户端仍使用 `/app/`，主持人/台架工作台仍使用 `/`。

- [用户端代码及运行说明](../apps/web/README.md)
- [临时 HTTPS 手机验收说明](../apps/web/qa/README.md)
- [总体整改核实与实施记录](../docs/product/EffMeet2_整改核实记录_2026-10-09.md)

## 启动方法

在**仓库根目录**运行，而不是在本目录复制一套服务：

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements-media.txt
./.venv/Scripts/python.exe scripts/run_participant.py
```

打开 `http://127.0.0.1:8765/app/`。另一终端执行 `./.venv/Scripts/python.exe scripts/seed_participant_demo.py --candidates 4`，用输出的新邀请链接展示合成候选。

历史完整快照可以从 `0e35865` 或 `923a8d0` 的本目录恢复；本轮去重前另生成了仓库外本地备份，不会上传数据库、密钥或冗余 ZIP。主仓库代码含原用户端、PWA、后端接入、合成数据与临时 HTTPS 工具，去重没有减少这些功能。

**120 秒有效期保持不变；打开链接不会续期。模拟机器人回执不等于真实机器人播报，实机/真实会议联调仍需独立验收。**
