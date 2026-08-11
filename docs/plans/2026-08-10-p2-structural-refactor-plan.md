---
title: P2 结构性重构计划（CLI argparse 化 · cache.py 拆分 · 评审证据迁出）
status: approved_not_started
created: 2026-08-10
updated: 2026-08-11
spec: none
spec_rationale: 纯工程重构，不含投资规则变更，故不适用 AGENTS.md 的 dated-spec 要求
execution_authorized: false
risk_tier: active-layer
review: AGY r1 (REQUEST_CHANGES → 已按裁决修订)
baseline_commit: 9db1675
---

# P2 结构性重构计划

> 本计划不构成实施授权。与 `2026-08-08-portable-a-stock-agent-skills-implementation-plan.md` 同例：需用户一次明确的"开始实施"表述，且可按 Phase 分别授权。

## 1. 背景

P0/P1 修复已于 2026-08-10 落地（`a21e217` 安装测试与 uv sync、`d5256b6` cache.py 死代码清理、`9db1675` schema bootstrap 连接泄漏）。本计划处理第一轮工程审查识别、但当时明确推迟的结构性债务：

- `cache.py` 3767 行、102 个顶层定义，一个文件里同时住着 schema 迁移、连接管理、领域规则、40 个 CLI 命令和分发逻辑；
- CLI 参数为手写解析，40 个命令**无一检查位置参数上限**，`cleanup 600519` 这类误用被静默忽略；
- `docs/reviews/` 247 个 tracked 文件占 docs 目录约 79%，是 AI 审查执行产物，持续膨胀源码仓。

### 1.1 用户决策记录

四个岔路口，用户在看过实测数据后均选最激进路径。其中两项（拆分与迁移同批、`add-holding` 改语义）制定方曾建议更保守方案并被明确否决；本计划因此以"把已接受的风险做可控"为设计目标，而非降低风险本身。

| 决策点 | 用户选择 |
|---|---|
| CLI 参数 | 全量迁移到 argparse subparsers，275 处 `cache.cmd_*()` 测试调用点重写 |
| `add-holding` 位置备注 | 改为显式 `--notes`，同批更新 skills |
| `cache.py` 拆分 | 与 argparse 迁移同一批完成 |
| `docs/reviews/` | 全部移出到独立 evidence 仓 |

### 1.2 决定计划形状的事实

真实生产库是活的：`~/.local/share/a-stock-agent/cache.db`，22 MB，**8 条持仓 / 16 条交易事件 / 177 条分析**，2026-08-10 13:22 仍在写入。

当前 55 处 `monkeypatch.setattr(cache, ...)` 中，`DB_PATH`(13处)、`_create_core_tables`、`SCHEMA_MIGRATIONS`、`_SCHEMA_INITIALIZED*` 是在 `get_db` / `_bootstrap_database_schema` 内部按模块全局解析的。**一旦这些函数搬到新模块，补丁不会报错，会变成静默空操作，测试转而写入真实持仓账本。** 这是本计划唯一的破坏性失败模式，因此 Phase 0 不可跳过、不可与后续阶段合并。

## 2. 硬约束（任何阶段不得违反）

1. **测试数量与断言不得净减少。** 275 处是业务行为测试（写库、算收益、判止损），不是参数解析测试。逐个转换、保留原断言，禁止"删掉重写一批新的"。
   把关方式：`pytest --collect-only` 的用例数**和** `tests/` 下 `assert` 总数都不得下降。仅数用例数无法发现"用例还在、断言被削弱"，这正是本约束要防的失败模式。
2. **`--confirm-write` 的前置严格性不得放宽。** 现状：必须位于子命令之前，其他前置 `--` 一律 exit 2。argparse subparsers 的自然行为会允许它出现在子命令之后——这是把唯一的写保护门从"位置严格"放宽为"位置随意"，必须显式禁止并留测试。
3. **`skills/` 的调用形式与输出 sentinel 不得改变**，唯一例外是本批授权的 `add-holding --notes`。受保护的 sentinel：`ANALYSIS_HIT` / `FUNDAMENTALS_HIT` / `FULL_MISS` / `ANALYSIS_PRICE_STALE`、`check-holdings` 的 `🔴`/`⚠️`、`checklist` 的 `达优/达格/未达/数据缺失` 与非零退出码、`l3-list` 的 `无结构化L3条件`、`holdings` 的 `stop_loss_15`/`stop_loss_20` 列。
4. **console script 入口不变**：`pyproject.toml` 的 `a-stock-cache = "a_stock_agent_runtime.cache:main"`，`cache.py` 必须保留 `main`。
5. **每个 Phase 独立 commit**，前一个 Phase 的门禁不过不进入下一个。用户要求"同一批做完"指一个工作批次，不是一个 commit——分阶段提交是让回归可二分定位的唯一手段。

## 3. Phase 0：安全网（前置，独立提交）

目标：让"补丁静默失效"从静默变成响亮失败。**必须在任何模块搬迁之前完成。**

- **主防线：在 `get_db` 内硬拦截生产库。** 解析出的路径若等于 `paths.cache_db_path()` 的真实默认值，且未显式设置逃生阀 `A_STOCK_ALLOW_PRODUCTION_DB=1`，直接 `raise RuntimeError`。这条防线在连接建立处生效，覆盖直接调用、`main()` 调用和子进程调用三条路径，不依赖任何 fixture 是否被正确写下。
  不采用"整轮结束比对生产库 sha256"作为主防线：生产库在测试期间可能被 cron 或用户正常写入，该校验会误报；一个会误报的守卫最终会被关掉。可保留为 session 级软告警，但不作为门禁。
- 新建 `tests/conftest.py`（当前不存在）：autouse function 级 fixture，默认把 `CACHE_DB_PATH` 指向 `tmp_path`，使"忘记隔离"的默认行为是安全的而非危险的。
- `src/a_stock_agent_runtime/cache.py`：`DB_PATH` 由 import 时绑定改为调用时解析。`paths.py:37` 的注释本就声称环境在调用时解析，代码却在 `paths.py:82-86` 和 `cache.py:97` 于 import 时求值——这是既有的注释与实现矛盾。复用现成的 `paths.cache_db_path()`。
- 同步把 13 处 `monkeypatch.setattr(cache, 'DB_PATH', ...)` 改为 `monkeypatch.setenv('CACHE_DB_PATH', ...)`；env 方案对后续模块搬迁天然免疫，且已实测会传播到子进程。
- `src/a_stock_agent_runtime/fetcher.py:855-885`：`_lookup_cached_industry` / `_lookup_cached_name` 惰性 `from ...cache import DB_PATH` 后自开 `sqlite3.connect`，绕过 `get_db`（无 schema bootstrap、无只读模式），且整体裹在 `except Exception: return None` 里——导入一旦失败会静默降级。收窄为具体异常，改用 `db.db_session()`。

**门禁**：全量 `bash scripts/check.sh` 通过；故意删掉某处 `CACHE_DB_PATH` 隔离，确认测试**红**而不是绿。

## 4. Phase 1：测试改走 `main(argv)`（独立提交）

这是让 argparse 迁移变安全的关键一步，先于 Phase 2。

- **前置：在 `tests/helpers.py` 增加 `cli_runner(argv) -> (code, stdout, stderr)`**，统一封装 `cache.main()` 调用与 stdio 捕获。`main()` 已在 `cache.py:3757` 捕获 `SystemExit` 并返回 int，因此不需要额外的退出拦截；helper 的价值是让 275 处转换有统一写法、且 stderr 断言不被漏写。
- 把 5 个测试文件里 275 处 `cache.cmd_xxx([...])` 逐个转换为 `cli_runner([...])` 或 `cli_runner(['--confirm-write', ...])`，`pytest.raises(SystemExit)` 改为断言返回码。
- **强制保留原有的具体中文 stderr 文本断言**（如 `'成本价必须为数字'`、`'股数必须大于0'`）。只断言返回码会让任何未预期的崩溃（`AttributeError`/`KeyError`）被误判为通过——退出码 1 无法区分"业务校验拒绝"和"代码崩溃"。每个原本断言消息文本的用例，转换后必须仍断言同一文本。
- 文件与当前调用数：`tests/research/test_cache.py`(155)、`test_missing_coverage.py`(51)、`test_edge_cases.py`(46)、`test_p0_contracts.py`(17)、`test_concurrency_resilience.py`(6)。
- 附带收益：现有测试**从不经过写确认门**，转换后每个 W1 用例都必须显式带 `--confirm-write`，安全边界首次被覆盖。
- 例外：`cmd_close_holding` 内部对 `cmd_sell_holding([...], single_lot=True)` 的调用（`cache.py:2210`）是生产代码路径，不属于本阶段，留到 Phase 2 一并改。

**门禁**：用例数与 `assert` 总数均 ≥ 转换前（开工前先记录两个基线数字）；`bash scripts/check.sh` 通过。

## 5. Phase 2：argparse subparsers（独立提交）

- 每个命令一个 subparser。自定义 `ArgumentParser` 子类覆写 `error()`，输出中文并 `sys.exit(1)`，以保持现有退出码与消息契约（`test_edge_cases.py:52-55` 等断言 `'成本价必须为数字'`）。
- 复用现有 `_parse_cli_finite_float`（`cache.py:693`）作为 `type=` 回调，中文消息一字不改。
- **全局 `--confirm-write` 不进 subparser**：继续由 `main` 在分发前手工剥离并校验位置，保留"仅允许前置"与 exit 2/3 语义（约束 2）。
- `add-holding` 改为 `<代码> <成本价> [股数] [--notes 备注]`，删除 `cache.py:1592` 的 `.isdigit()` 启发式；同批更新 `skills/a-stock-monitor/SKILL.md:61,143-144`、`skills/a-stock-monitor/references/data-operations.md:14-15` 和 `cache.py` docstring:31。传播面已全仓 grep 核实为仅此三处（CHANGELOG 中的提及为历史散文；cron 脚本只用 `check-holdings`；`policy_replay.py` 与 runtime 零耦合）。
- `--help` 契约：模块 docstring 目前是 `--help` 的输出，且被 `tests/test_command_classification.py` 的两个测试钉住（P1 新增）。改为由 argparse 生成 help 后，这两个测试须重写为断言"每个命令与 `--confirm-write` 出现在 `parser.format_help()` 中"——**契约保留，实现改变**。
- 删除死代码：`check = cmd_check` 别名（`cache.py:3649`，全仓零导入方）。
- 核实 `requests` 顶层导入（`cache.py:77`，`# noqa: F401`）：真实 HTTP 在 `market_quotes.py`，14 处 `monkeypatch.setattr(cache.requests, 'get', ...)` 可能已在打空气。逐个确认是否仍有断言效力，无效则连同导入一并删除。

**门禁**：`bash scripts/check.sh` 通过；`uv run a-stock-cache --help` 人工核对；用 `skills/` 里每一条已文档化的调用形式做一遍冒烟（含 heredoc 形式的 `set-analysis`）。

## 6. Phase 3：cache.py 拆分（独立提交，可再分为 3a/3b）

目标布局（`cache.py` 保留为 CLI 入口以维持 console script）：

| 模块 | 内容 | 约行数 |
|---|---|---|
| `cache.py` | parser 定义、`COMMANDS`、`COMMAND_CLASSIFICATION`、`main` | ~700 |
| `db.py` | `get_db` / `db_session` / 路径解析 / 只读标志 | ~130 |
| `schema.py` | `SCHEMA_MIGRATIONS`、建表、backfill、`_bootstrap_database_schema` | ~420 |
| `domain.py` | 时间/TTL、框架推断、止损系数、纯校验器、止损状态判定 | ~330 |
| `store.py` | 数据访问 helper（基本面、快照、`get_watchlist_rows`） | ~450 |
| `commands_*.py` | 按表分组的 `cmd_*`（analysis / holdings / monitor / admin） | ~2500 |

关键处理：

- `_READ_ONLY_REQUEST` 是唯一真正跨桶的全局（`main` 写、`get_db` 读）→ 改为 `db.set_read_only(bool)`。`_SCHEMA_INITIALIZED*` 只在 `get_db` 内读写，随 `db.py` 走，无需穿线。
- **打破循环依赖**：`checklist.py:12` 顶层 `import cache`，只为 `checklist.py:388` 的 `cache.get_fundamentals`；改为 `from a_stock_agent_runtime import store`。随后可删除 `infer_framework`(`cache.py:222`) 与 `get_stop_loss_pct`(`cache.py:238`) 里为规避循环而写的两处惰性 import。
- `_backfill_holding_metadata` 既是 ledger 迁移 `025`，又被 4 个 `cmd_*` 当防御性重跑调用（`cache.py:1819/2285/2338/2433`）→ `commands_holdings.py` 需 import `schema.py`，这是本次拆分唯一的"命令层依赖迁移层"边，接受并注释说明。
- 先拆最安全的三块（止损状态判定 56 行、时间/TTL 36 行、纯校验器 ~150 行），验证通过后再拆 schema 那 399 行。

**门禁**：每个子步骤后 `bash scripts/check.sh` 通过；`tests/test_import_graph.py` 扩展为断言新模块无循环导入，并**显式禁止 `commands_*.py` 反向 `import cache`**（依赖必须严格单向：`cache.py` → `commands_*` → `store`/`schema`/`db`/`domain`）；Phase 0 的生产库硬拦截必须始终生效。

## 7. Phase 4：docs/reviews 迁出（独立提交）

- 247 个 tracked 文件迁至独立 git 仓（建议 `~/a-stock-agent-evidence`），本仓 `docs/reviews/` 只留一个 `README.md` 索引说明去向与查阅方式。
- 更新四个引用方：`docs/README.md`、`docs/migration/README.md`、`docs/plans/2026-08-08-*.md`、`docs/specs/2026-08-08-*.md`。
- `AGENTS.md` 增加一条：新增审查证据写仓外，不进源码仓。
- 顺带修两处已确认的文档错误：`docs/operations.md:51-55` 说 "append the global `--confirm-write` flag"，与前置强制的实现矛盾；`skills/a-stock-monitor/references/backtest.md:22-25` 指向不存在的 `tools/policy_replay.py`（实际在 `skills/a-stock-monitor/scripts/policy_replay.py`）。

**门禁**：`uv run python scripts/validate.py` 通过（它会检查 skills 内引用的相对路径存在）；全仓 grep 无悬空 `docs/reviews/` 链接。

## 8. 验证

每个 Phase 结束后执行：

```bash
bash scripts/check.sh          # pytest + ruff + validate + qa smoke + cron smoke
```

Phase 特有的额外验证：

```bash
# Phase 0：确认硬拦截真的会响
uv run python -c "from a_stock_agent_runtime import db; db.get_db()"   # 期望 RuntimeError
uv run pytest tests/research/test_cache.py -q                          # 期望绿
# 再手工删掉某处 CACHE_DB_PATH 隔离，期望红而不是静默写真实库

# Phase 1/2：测试规模与断言强度都不得缩水
uv run pytest --collect-only -q | tail -1                     # 用例数，与转换前比对
grep -rc "assert " tests/ | awk -F: '{s+=$2} END {print s}'   # 断言数，与转换前比对

# Phase 2：CLI 契约冒烟（临时库，不碰真实状态）
export CACHE_DB_PATH=$(mktemp -d)/smoke.db
uv run a-stock-cache --help
uv run a-stock-cache set-flag 000001 yellow x ; echo "期望 3，实际 $?"
uv run a-stock-cache set-flag --confirm-write 000001 yellow x ; echo "期望 2（门必须前置），实际 $?"
uv run a-stock-cache bogus ; echo "期望 1，实际 $?"

# Phase 3：无循环导入
uv run python -c "import a_stock_agent_runtime.cache, a_stock_agent_runtime.checklist"

# 全程：真实持仓库未被触碰（软校验，生产写入会造成误报，仅参考不作门禁）
sha256sum ~/.local/share/a-stock-agent/cache.db
```

## 9. 一处必须记录的权衡更正

制定方在向用户呈报时，曾把"测试改走 `main(argv)` 后写确认门首次被覆盖"作为接受全量 argparse 迁移的理由之一。AGY 复审指出、制定方确认：**该安全收益完全由 Phase 1 提供，与 argparse 无关。** Phase 1 单独做完即可拿到全部覆盖收益。

因此 Phase 2 的实际依据只剩用户偏好，其可量化收益为：40 个命令统一的参数上限校验、每子命令自带 `--help`、删除约 150 行手写解析；成本为 275 处测试改写风险 + `add-holding` 语义变更传播到 live skill。此前已实测推翻"可净删几百行"的说法（实际仅 4 处手写循环，40 个命令中仅约 7 个带 flag，115 个 `sys.exit(1)` 绝大多数是业务校验而非参数解析）。

用户已在知情下选择全量迁移，计划按此执行；此处仅确保该权衡被明确记录，而非隐含在"安全收益"的表述里。

## 10. AGY 复审记录（r1，2026-08-10）

Verdict：`REQUEST_CHANGES`，4 个 blocking。只读校验通过（计划文件 sha256 前后一致）。裁决如下，原始产物未入本仓（依 Phase 4 决策，评审证据不再写入源码仓）。

| # | AGY 主张 | 裁决 | 依据 |
|---|---|---|---|
| B1a | session 级 sha256 会被生产库并发写入误报 | **采纳** | 会误报的守卫最终会被关掉；改为 `get_db` 内硬拦截 |
| B1b | fixture 环境变量不传播到子进程 | **驳回** | 实测 `monkeypatch.setenv` 正常传播；`setattr`→`setenv` 恰是子进程隔离的修复手段 |
| B2 | 断言改返回码会丢失中文 stderr 断言 | **采纳** | 计划真实疏漏，已加硬性保留要求 |
| B3 | `sys.exit(1)` 会击穿 pytest 进程 | **驳回** | `cache.py:3757` 已 `except SystemExit: return int(...)`；实测该模式 pytest 全绿 |
| B4 | `_READ_ONLY_REQUEST` 跨用例污染，应默认重置为 `True` | **驳回，其修复有害** | `main()` 每次按分级赋值（`:3755`）、`finally` 归位（`:3763`）；改默认 `True` 会让直接 `get_db()` 的 fixture 变只读，破坏测试数据准备 |
| N1 | 全量 argparse 性价比应回报用户 | 采纳 | 见第 9 节 |
| N2 | `--collect-only` 无法发现断言被削弱 | 采纳 | 已加 `assert` 总数双计数 |
| N3 | `add-holding` 变更可能有未列出的传播面 | 已验证无需处置 | 全仓 grep 确认仅三处 |
| N4 | 禁止 `commands_*.py` 反向 import cache | 采纳 | 已加入 Phase 3 门禁 |

模式记录：两轮 AGY 复审（P0/P1 代码、本计划）一致显示，其在"这段代码实际怎么跑"上不可靠（上轮错判 SQLite DDL 事务语义，本轮错判 pytest/monkeypatch 运行时行为，均可用一次实测证伪），在"这个设计缺了什么"上有价值。后续送审应继续把 blocking 当作待验证假设逐条实测。

## 11. 风险登记（用户已知悉并接受）

| 风险 | 缓解 |
|---|---|
| 拆分 + argparse 同批，回归难定位 | 分 Phase 独立提交，可 `git bisect` 到阶段 |
| 275 处测试重写导致覆盖静默下降 | 逐个转换而非删除重写；用例数与 `assert` 数双计数把关 |
| 转换后用例还在但断言被削弱 | 原断言具体中文文本的用例，转换后必须仍断言同一文本 |
| `add-holding` 语义变更打断 live skill | 同批更新 skills 全部三处文档化调用；`scripts/validate.py` 把关引用完整性 |
| 测试误写真实持仓账本 | Phase 0 在 `get_db` 硬拦截生产库路径（覆盖直接调用/`main()`/子进程三条路径），外加默认 tmp 库的 autouse fixture |
| argparse 放宽 `--confirm-write` 位置 | 该 flag 不进 subparser，由 `main` 手工把守并留专项测试 |
