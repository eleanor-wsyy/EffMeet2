> 2026-10-09 实施核实补充：本机原 88 项测试全通过，未复现本文的 WAL 故障；部分结论和建议不能直接照搬。实际修复及保留边界见 [整改核实记录](EffMeet2_整改核实记录_2026-10-09.md)。本文原始调查内容保留供对照。

# EffMeet2 总体整改方案 v1

> 基线：`0e35865`　日期：2026-10-09　**距初赛提交截止 12 天（10.21）**
> 提出：A 位（智能设计助手代）　范围：仓库体检（2026-10-09）发现的五个问题

---

## 0 · 三条原则

1. **只加固，不返工。** 全量测试证明 B/C/D 现有逻辑**零业务缺陷**——把 WAL 关掉后 failures 从 3 变 0。下面五个问题没有一个是"写错了"，全是"没考虑到某种运行环境"。
2. **最小改动，独立合入。** 每条改动互不依赖，谁有空谁做，不用等别人。
3. **不阻塞任何人。** 不删 D 正在维护的目录；不推翻 D 那个正确但被我误建议过的决定。

---

## 1 · 总表

| 编号 | 优先级 | 问题 | 位置 | 责任人 | 工作量 | 验收标准 |
|---|---|---|---|---|---|---|
| **P0-1** | 🔴 P0 | WAL 模式下并发写必报 `readonly` | `services/controller/store.py:44/110/304` | **B** | ~15 行 | 4 线程并发确认：0 报错，且 `robot.calls == 1` |
| **P1-1** | 🟡 P1 | 兜底把环境错误伪装成业务错误 | `services/controller/bench.py:121` | **C** | ~6 行 | 异常时日志能看见原始 `OperationalError` |
| **P1-2** | 🟡 P1 | 整仓快照副本（122/250 文件） | `用户端APP（10.7）/` | **D**（确认后） | 1 条命令 | 仓库文件数 250 → 128 |
| **P2-1** | ⚪ 待定 | 米白背景是否为你要求 | `apps/web/styles.css:12` | **宁导** | 一句话 | — |
| **P2-2** | 🟢 P2 | 演示节奏（种子 120 秒过期） | 演示脚本 | **A（我）** | — | 演示流程里写明 |

**明确不做**：给种子脚本加 `--ttl`。D 的判断是对的（见 §6）。

---

## 2 · P0-1 · WAL 并发写失败（责任人：B）

### 2.1 现象

```
sqlite3.OperationalError: attempt to write a readonly database
  services/controller/store.py:110   conn.execute("BEGIN IMMEDIATE")
  services/controller/store.py:304   with self.db(write=True)
```

全量 88 项测试中 **6 项同源**（5 个直接报错 + 1 个被兜底伪装）。

### 2.2 已排除的可能（不必重复排查）

| 验证 | 结果 |
|---|---|
| 换到 D: 工作区目录 | 同样失败 → 不是临时目录问题 |
| 换执行通道（非沙箱）重跑 | 同样失败 → 不是工具沙箱问题 |
| **脱离项目的最小复现**（4 行建表 + 并发 `BEGIN IMMEDIATE`） | **WAL 照样炸，DELETE 全过** → 不是本项目代码写法问题 |
| 运行时把 `journal_mode` 换成 DELETE 跑全量 | **failures 3 → 0** → 因果确认 |

> 补充：本机（Win11 + SQLite 3.53.1）100% 复现；B 自己机器报 61 项通过，说明他那台不触发。
> **所以这不是"你的代码错了"，是"这段代码在某些机器上会炸"。** 决赛用异地笔记本，属于"可能没事、出事就现场翻车"，值得花 15 行买保险。

### 2.3 改法

**① `store.py` 顶部加 `import logging`**（现在没有）。

**② `Store` 类里加一个类级开关**（放在 `class Store(ResponseTracking):` 下面）：

```python
    # 部分机器（Win11 + 某些安全软件/文件系统）在 WAL 模式下并发写会报
    # "attempt to write a readonly database"。一旦触发，全局降级为 DELETE。
    _journal_fallback = False
```

**③ 把 `db()` 里的 `BEGIN IMMEDIATE` 换成一次可降级的调用**（约 104–118 行）：

```python
    @contextmanager
    def db(self, write=False):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        if Store._journal_fallback:
            conn.execute("PRAGMA journal_mode=DELETE")
        try:
            if write:
                self._begin(conn)
            yield conn
            if write:
                conn.commit()
        except Exception:
            if write:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
            raise
        finally:
            conn.close()

    def _begin(self, conn):
        """BEGIN IMMEDIATE；遇到 WAL 不可写则降级为 DELETE 后重试一次。"""
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "readonly" in str(exc) and not Store._journal_fallback:
                Store._journal_fallback = True
                logging.warning("SQLite WAL 不可用（%s），已降级为 DELETE 日志模式", exc)
                conn.execute("PRAGMA journal_mode=DELETE")
                conn.execute("BEGIN IMMEDIATE")
            else:
                raise
```

> ⚠️ **两个坑，别踩**：
> 1. **不要在 `PRAGMA journal_mode=WAL` 那一行 try/except**——报错发生在 `BEGIN IMMEDIATE`，那行 PRAGMA 本身永远是成功的。
> 2. **加大 `busy_timeout` 无效**，我试过 30 秒，仍然失败。别在这上面浪费时间。
>
> WAL / DELETE 都是**持久化**在数据库文件里的，所以正常路径下每次连接不用重设 PRAGMA，只有降级后才需要——这也是上面 `if Store._journal_fallback:` 写成条件的原因。

**④（可选，顺手）在 `app.py` 把这类错误映射成 503**（`app.py:104` 附近照现有 `domain_error` 的写法加一个）：

```python
    @app.exception_handler(sqlite3.OperationalError)
    async def store_error(request, exc):
        return error(503, "STORE_BUSY", "本机存储暂时不可写，请重试。")
```

需在 `app.py` 加 `import sqlite3`。这样即使降级也没兜住，用户拿到的是"请重试"而不是 500。

### 2.4 验收

```bash
./.venv/Scripts/python.exe -m unittest tests.test_controller.ControllerTests.test_concurrent_confirm_dispatches_once
```

通过即可。更彻底的验证是跑全量，本机预期从 `failures=3, errors=5` 变为 **只剩 1 个**（`test_livekit`，缺 `requirements-media.txt` 里的依赖，与本次无关）。

**红线复核**：改完请确认 `robot.calls` 仍为 1——即使在 WAL 报错的情况下它现在**就已经是 1** 了，说明幂等不依赖数据库事务，改动不应破坏这一点。

---

## 3 · P1-1 · 兜底掩盖真因（责任人：C）

### 3.1 问题

`services/controller/bench.py:121`：

```python
code = exc.code if isinstance(exc, DemoError) else "ANALYSIS_FAILED"
```

任何非 `DemoError` 的异常都被吞成 `ANALYSIS_FAILED`。**后果**：WAL 报 `readonly` 时，测试看到的是 `ANALYSIS_FAILED != CONTEXT_CHANGED`，看起来像语义 bug——我这次排查多花了半小时才定位到真因。

### 3.2 改法

```python
        except Exception as exc:
            if isinstance(exc, DemoError):
                code = exc.code
            else:
                logging.exception("bench job 因非业务异常失败，原始异常见上")
                code = "ANALYSIS_FAILED"
```

**另外还有一个连带隐患，建议一起处理**：这个 `except` 块自己也要写数据库（`UPDATE bench_jobs SET status='failed'`）。**如果失败原因正是数据库不可写，这次写入也会失败**，任务会永远卡在 `running`。建议把那次 UPDATE 单独包一层 `try/except`，失败时至少打日志。

### 3.3 验收

制造一个非业务异常（或直接看日志），确认日志里能读到原始 `OperationalError` 而不是只有一个 `ANALYSIS_FAILED`。

---

## 4 · P1-2 · 整仓快照副本（责任人：D，需先确认）

### 4.1 现状

`用户端APP（10.7）/` 不是 APP 副本，**是整仓快照**（README / apps / assets / contracts / docs / firmware / hardware / scripts / services / tests / tools 全套）。

- 仓库 250 个受控文件中 **122 个（≈49%）在这个目录里**，磁盘 4.6MB
- `app.js` / `index.html` / `state.js` / `styles.css` 与根 `apps/web/` **逐字节相同**
- **里面还有一份 `store.py`** → 同一个 WAL bug 仓里有两份，改根那份快照不会跟着好

由 `4cba335`（2026-10-07）引入。

### 4.2 为什么现在没删

D 最新的提交标题是 *"Sync participant standalone bundle"*——他在主动维护两份同步。这时删会打断他手上正在做的事。

### 4.3 做法（D 确认"根 `apps/web/` 是唯一真源"之后）

```bash
git rm -r --cached "用户端APP（10.7）"
rm -rf "用户端APP（10.7）"
git commit -m "chore: 移除 10.7 整仓快照副本，根 apps/web 为唯一真源"
```

历史不会丢，`4cba335` 那次的内容在 git 里永远可回溯。

**顺带建议**：把 `用户端APP（*）` 这类目录加进 `.gitignore`，防止以后再有人整仓复制进来。

---

## 5 · P2-1 · 米白背景（待宁导一句话）

`apps/web/styles.css:12` 把 `.app-shell` 背景改成了 `#FFFFFF → #FFEFBA` 米白渐变。D 的 README 写这次调整是"按用户要求"。

- **品牌色没动**：`--brand: #F0522E` 仍在，`--coral` 渐变仍在，麦克风按钮仍用品牌色。我之前报的"品牌色被改"是误报，作废。
- **需要确认**：米白背景是不是你要求 D 改的？
  - **是** → 我同步外壳环灯（珊瑚橙）和 Ardot 高保真稿，否则机器人暖、界面冷，现场会打架。
  - **不是** → 尽快纠正，越晚改越贵。

---

## 6 · 明确不做：种子脚本不加 `--ttl`

`scripts/seed_participant_demo.py:21` 的注释写着：

> *"This helper deliberately keeps the server's 120s deadline and auth gates."*

**D 是对的，我上一轮建议加 `--ttl` 是错的。** 120 秒是我们对外宣称的产品规则（候选超时即弃权），种子脚本放开等于自己打自己脸。

**真问题在演示节奏，不在代码**：我首次 seed 后过了约 5 分钟才打开页面，三个候选全 `expired`（超时 288 秒），核心的"确认→提醒"交互当场演不出来。

**解法改演示方式，不改代码**（A 位，我自己做）：
- 演示脚本里定死"种子后 60 秒内必须走完确认"；
- 准备一条随时可重跑的种子命令放在手边，讲砸了立刻补一次。

---

## 7 · 执行顺序

```
第 1 批（互不依赖，可并行）
  ├─ P0-1  WAL 降级        → B    🔴 最优先
  ├─ P1-1  bench 兜底      → C
  └─ P2-2  演示脚本补节奏  → A（我）

第 2 批（需先确认）
  ├─ P1-2  删快照          → D    ⚠️ 等 D 确认"根是真源"
  └─ P2-1  米白背景        → 宁导 ⚠️ 等你一句话
```

**唯一的硬依赖**：P1-2 必须等 D 确认，不能抢跑。

---

## 8 · 派活文案（可直接复制）

### 给 B

> 仓库体检发现一处隐患，不是逻辑错，但你这边 15 行能买个保险：
> `services/controller/store.py` 无条件设了 `PRAGMA journal_mode=WAL`（第 44 行），在部分 Windows 机器上多线程并发 `BEGIN IMMEDIATE` 会报 `attempt to write a readonly database`，我本机 100% 复现（已排除目录/沙箱/项目写法，做了脱离项目的最小复现，换 DELETE 后全量测试 failures 3→0）。
> 建议在写事务层加降级：捕获 readonly → 切 DELETE 重试一次。注意报错在 `BEGIN IMMEDIATE` 不在 PRAGMA 那行；加大 busy_timeout 无效。详细代码见 `docs/product/EffMeet2_总体整改方案_v1.md` §2.3。
> 顺带一提：即使在报错情况下 `robot.calls` 依然是 1，说明你的幂等不依赖数据库事务——这点挺扎实的。

### 给 C

> `services/controller/bench.py:121` 那行 `code = exc.code if isinstance(exc, DemoError) else "ANALYSIS_FAILED"` 把非业务异常全吞成 `ANALYSIS_FAILED`。昨天排查 WAL 问题时，真因（sqlite readonly）被它伪装成业务错误，多花了半小时才定位。
> 建议非 `DemoError` 分支加 `logging.exception(...)` 保留原始栈。另外那个 except 块自己也要写库——如果失败原因正是库不可写，UPDATE 会一起失败，任务永远卡 running，建议单独包一层。

### 给 D

> 两件事：
> 1. `用户端APP（10.7）/` 是整仓快照不是 APP 副本，占了 250 个受控文件里的 122 个，里面还有一份 `store.py`（同一个 bug 两份）。**等你说"根 `apps/web/` 是唯一真源"我就删**，现在不动，怕打断你正在做的 sync。
> 2. 种子脚本不加 `--ttl` 这个决定**你是对的，我收回上次的建议**。120 秒是产品规则，放开就是自己打自己脸。演示节奏的问题我改成在演示脚本里解决。
