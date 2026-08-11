---
title: P2 结构性重构计划（CLI argparse 化 · cache.py 拆分 · 评审证据迁出）
status: completed
created: 2026-08-10
updated: 2026-08-11
closed: 2026-08-11
spec: none
spec_rationale: 纯工程重构，不含投资规则变更，故不适用 AGENTS.md 的 dated-spec 要求
execution_authorized: phase_0_4
risk_tier: active-layer
review: AGY r2 + Codex adversarial (REQUEST_CHANGES → addressed)
release: v0.1.2
deployment_runtime: 0.1.2-52aa56191174
baseline_commit: 9ad3b8e
implementation_head: 7b6bb62
phase_4_source_snapshot: c493aa8dc4f2649c6241587f55be94f0a11011fb
phase_4_evidence_commit: 76d643b55c02c05f263a7c910c7c3cb6a843040f
---

# P2 结构性重构计划

> 本计划不构成实施授权。仓库内 Phase 0-3 可由用户一次明确的“开始实施 P2”授权；Phase 4 涉及创建仓外 Git 仓和删除本仓 tracked 文件，必须另行明确授权。

> 2026-08-11 执行记录：用户分别授权并完成 Phase 0-3 与 Phase 4。Phase 4 将 247 个证据文件迁至 `/home/lin/a-stock-agent-evidence` 的提交 `76d643b`；逐文件路径、大小和 SHA256 与 manifest 完全一致后，源仓仅保留 tombstone。Phase 0-3 最终门禁为 627 tests、971 个 `assert` token，`bash scripts/check.sh` 全部通过；Phase 4 收尾门禁见下方完成记录。

Phase 0-3 实施提交：

- `a8253f5` — Phase 0：测试数据库隔离与显式只读访问；
- `0f3aec1` — Phase 1：冻结 CLI/W1 契约；
- `34e80b1` — Phase 2：argparse subparsers 与 `add-holding --notes`；
- `3420a84` — Phase 3a：领域规则拆分；
- `dd29f7e` — Phase 3b：DB/schema/store 拆分；
- `7b6bb62` — Phase 3c：commands 拆分与入口收口。

Phase 4 完成记录：

- 最后完整包含源证据的提交：`c493aa8dc4f2649c6241587f55be94f0a11011fb`；
- 外部 evidence 提交：`76d643b55c02c05f263a7c910c7c3cb6a843040f`；
- manifest：247 项，SHA256 `764454a8e079e416d9e4a95b547a8bf9fb21037c3a61b45f8262db0f0ee05072`；
- Phase 4 门禁：双仓 working tree/索引符合预期，manifest 复核通过，`bash scripts/check.sh` 为 627 tests 全部通过；
- 恢复与定位说明：`docs/reviews/README.md`。

发布记录：reviewer 发现的跨命令 helper 早绑定问题已在 `8252baa` 修复并经 AGY 复审 `PASS`；release commit `52aa561` 标记为 `v0.1.2`，版本化 runtime `0.1.2-52aa56191174` 已于 2026-08-11 部署。最终门禁为 628 tests，生产只读 smoke 通过，配置与 crontab 指纹不变，未执行数据库 schema 迁移。

## 1. 背景与当前基线

P0/P1 修复和 `v0.1.1` 发布已完成。本计划只处理结构性工程债务，不改变投资规则、数据库 schema、生产 cron、active Skill 入口或外部通知策略：

- `src/a_stock_agent_runtime/cache.py` 为 3769 行，混合 schema、连接管理、领域规则、40 个 CLI 命令和分发逻辑；
- 40 个命令使用手写参数解析，位置参数上限不统一，`cleanup 600519` 等误用可被静默忽略；
- `docs/reviews/` 有 247 个 tracked 文件，未来继续把执行产物提交到源码仓会持续膨胀。

开工基线固定为：

| 项目 | 基线 |
|---|---:|
| Git commit | `9ad3b8e` |
| pytest collected | 615 |
| `tests/**/*.py` 中 `assert` token | 941 |
| 全仓 `cache.cmd_*()` 测试调用 | 276（其中五个 research 文件 275） |
| `monkeypatch.setattr(cache, ...)` | 46 |
| `DB_PATH` monkeypatch | 14 |

生产数据库是活动状态。计划和测试不得读取、写入、哈希比较或依赖生产数据库内容；生产 writer、cron 和 active client 不属于本计划授权范围。

### 1.1 用户决策与审查修订

| 决策点 | 最终范围 |
|---|---|
| CLI 参数 | 全量迁移到 argparse subparsers；保留业务函数直接单测，不再重写 276 处调用 |
| `add-holding` 备注 | 改为显式 `--notes`，同步修改 Skill、帮助和相关测试 |
| `cache.py` 拆分 | 与 argparse 属于同一工作批次，但按独立 commit 和可回滚子阶段推进 |
| `docs/reviews/` | 迁到独立 evidence 仓，但作为 Phase 4 单独授权、校验和回滚 |

AGY r2 与 Codex 对抗复核确认并修正了四项关键事实：

1. 无条件生产 DB 硬拦截会让正常 CLI/cron 默认失败，禁止实施；
2. `cache.requests` 与 `market_quotes.requests` 是同一模块对象，现有 patch 有效，不得按“空气 patch”删除；
3. `set-flag --confirm-write ...` 当前返回 3，不是 2；
4. 让测试改走 `main(argv)`不能解决拆模块后的 monkeypatch 绑定失效。

## 2. 硬约束

1. **生产行为不变。** 不新增 `A_STOCK_ALLOW_PRODUCTION_DB` 等逃生阀，不在生产代码中判断 `PYTEST_CURRENT_TEST`，正常 CLI 和 cron 不需要新增环境变量。
2. **测试强度不降。** collected tests 不低于 615、`assert` token 不低于 941；不得删除原业务断言来换取计数通过。新增参数化测试可以增加基线，不能替代原业务测试。
3. **W1 门保持严格。** `--confirm-write` 只能位于子命令前。现行契约是：W1 缺少或错放该 flag 返回 3；未知的前置全局 `--*` 返回 2；均不得打开写事务。
4. **Skill 与 sentinel 保持。** 唯一已授权的 CLI 语义变化是 `add-holding --notes`。受保护输出包括 Research cache sentinel、`check-holdings` 图标、checklist 档位与非零退出码、L3 空状态和 holdings 止损列。
5. **入口保持。** `a-stock-cache = "a_stock_agent_runtime.cache:main"` 不变，`cache.py` 保留 `main`。
6. **Patch 必须迁到真实 owner。** 禁止依赖 `cache.__getattr__` 等无法转发模块属性赋值的动态代理；每次提取模块时同步迁移相应 patch，并验证 mock 确实改变被测行为。
7. **阶段独立。** 每个 Phase 独立 commit；Phase 3a/3b/3c 也分别提交。门禁失败时不进入下一阶段。
8. **外部状态单独授权。** Phase 4 的仓外创建、复制和本仓 tracked 文件删除不得由 Phase 0-3 的仓库内实施授权推导。

## 3. Phase 0：测试 DB 隔离与只读访问基线

目标：消除模块搬迁时测试误写生产数据库的路径，同时不污染或封禁生产运行时。

### 3.1 测试侧隔离

- 新建根 `tests/conftest.py`，用 autouse function fixture 将 `CACHE_DB_PATH` 设置为当次 `tmp_path / "cache.db"`；fixture 记录设置前的外部默认路径，并在测试结束前断言当前解析路径不是该外部路径。
- `CACHE_DB_PATH` 必须在每个测试调用运行时代码前生效，并自然传播给测试创建的子进程。
- `cache.py` 不再在 import 时绑定 `DB_PATH`；所有连接和 CLI 路径展示统一在调用时通过 `paths.cache_db_path()` 解析。
- 将 14 处 `monkeypatch.setattr(cache, "DB_PATH", ...)` 改为 `monkeypatch.setenv("CACHE_DB_PATH", ...)`。
- 在 `tests/test_side_effect_boundaries.py` 增加测试侧守卫回归：fixture 路径位于 pytest 临时目录，R0/W1/子进程均不能解析到记录的外部默认路径。

不实现以下方案：

- 在 `get_db()` 无条件封禁默认 DB；
- `A_STOCK_ALLOW_PRODUCTION_DB=1` 逃生阀；
- 在生产模块中检测 pytest 环境变量；
- 用活动生产库 SHA256 作为测试门禁。

### 3.2 显式只读会话

- 先在现有 DB 层提供 `read_only_db_session()`：使用 SQLite URI `mode=ro`，不创建目录、不 bootstrap schema、不执行 backfill。
- `fetcher.py` 的 `_lookup_cached_industry` / `_lookup_cached_name` 继续 fail-soft，但改用该显式只读会话；只捕获“数据库不存在、表不存在、连接失败”等预期 SQLite/文件异常，不吞掉导入和编程错误。
- Phase 3 创建 `db.py` 后再把该 helper 原样迁入；Phase 0 不引用尚不存在的 `db.py`。

### 3.3 Phase 0 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest \
  tests/test_paths.py \
  tests/test_cli_contract.py \
  tests/test_side_effect_boundaries.py \
  tests/research/test_fetcher.py -q
bash scripts/check.sh
```

额外断言：正常非 pytest 环境解析默认路径时不会因为测试守卫抛错；测试和测试子进程解析出的路径均为临时路径。

## 4. Phase 1：冻结 CLI 与 W1 契约

目标：在引入 argparse 前，用少量入口契约测试固定现行行为；保留 276 处业务函数直接调用。

- 不新增 `cli_runner`，不把 `cache.cmd_*()` 业务单测批量改成 `main(argv)`。
- 扩展 `tests/test_cli_contract.py`：从 `COMMAND_CLASSIFICATION` 参数化覆盖全部 W1 命令，断言缺少前置确认时返回 3、输出中文提示且不打开数据库。
- 固定 `--confirm-write` 位置契约：
  - `a-stock-cache set-flag --confirm-write ...` → 3；
  - `a-stock-cache --bogus set-flag ...` → 2；
  - 只有 `a-stock-cache --confirm-write set-flag ...` 才进入子命令参数验证。
- 为 40 个命令建立 parser 输入矩阵：最短合法 argv、最长合法 argv、额外位置参数、未知 option。Phase 1 记录当前预期，Phase 2 复用同一矩阵验证 argparse。
- 原来断言具体中文错误文本的用例继续直接调用业务函数并保留原断言。

**门禁**：focused CLI tests 与 `bash scripts/check.sh` 全部通过；记录更新后的 collected/assert 基线。

## 5. Phase 2：argparse subparsers

- 每个命令一个 subparser。自定义 `ArgumentParser.error()` 只负责 argparse 自身错误；现有业务校验函数继续输出原中文文本和退出码。
- `main()` 在 argparse 分发前手工处理全局 `--confirm-write`，严格保持 Phase 1 固定的 2/3 退出码契约。
- 每个 subparser 明确位置参数上限；额外参数和未知 option 必须失败，不再静默忽略。
- `add-holding` 改为 `<代码> <成本价> [股数] [--notes 备注]`，删除 `.isdigit()` 推断备注的语义。同步更新：
  - `cache.py` help/docstring；
  - `skills/a-stock-monitor/SKILL.md`；
  - `skills/a-stock-monitor/references/data-operations.md`；
  - `tests/research/test_edge_cases.py` 的位置备注测试；
  - 全仓检索发现的其他非历史调用。
- `--help` 改由 argparse 生成，测试必须断言全部命令、全局确认门和每个子命令 help 可发现。
- 不在本阶段清理 `cache.requests` 或 `check = cmd_check`；它们与 argparse 验收无关，留待真实 owner 迁移时处理。

**门禁**：

```bash
uv run pytest tests/test_cli_contract.py tests/test_command_classification.py \
  tests/research/test_edge_cases.py -q
uv run a-stock-cache --help
bash scripts/check.sh
```

此外，用 `skills/` 中每一种文档化调用形式在临时数据库和通知禁用环境下冒烟，包括 `set-analysis` heredoc 与 `add-holding --notes`。

## 6. Phase 3：cache.py 分步拆分

目标依赖方向：

```text
cache.py → commands_* → store / schema / db / domain
checklist.py → store / domain
```

禁止 `commands_*.py` 反向 import `cache`。跨模块 helper 使用模块限定调用，例如 `import domain; domain.utc_now()`，避免 `from domain import utc_now` 的早绑定使 monkeypatch 静默失效。

### 6.1 Phase 3a：纯叶子领域逻辑

- 提取 `domain.py`：时间/TTL、纯校验器、框架推断、止损系数和止损状态判定。
- 同步把 `utc_now`、`is_expired`、`_is_a_share_trading_hours`、`datetime` 等 patch 改到 `domain` 或实际使用模块。
- 每类 patch 至少保留一项“改变 mock 返回值会改变命令结果”的回归断言。

### 6.2 Phase 3b：DB、schema 与 store

- 提取 `db.py`：动态路径、`db_session`、`read_only_db_session`、schema 初始化状态和 `read_only_scope()`。
- 提取 `schema.py`：迁移清单、建表、backfill 和 bootstrap。
- 提取 `store.py`：基本面、快照、watchlist 等数据访问 helper。
- 将 `_SCHEMA_INITIALIZED*`、`SCHEMA_MIGRATIONS`、`db_session`、行情读取等 patch 改到真实 owner。
- `checklist.py` 从顶层 `import cache` 改为依赖 `store`/`domain`，消除循环依赖。

### 6.3 Phase 3c：commands 与入口收口

- 按领域提取 `commands_analysis.py`、`commands_holdings.py`、`commands_monitor.py`、`commands_admin.py`；不以预计行数作为验收条件。
- `cache.py` 只保留 parser、`COMMANDS`、`COMMAND_CLASSIFICATION`、兼容性所必需的显式导入和 `main()`。
- `_READ_ONLY_REQUEST` 改为 `with db.read_only_scope(classification == "R0")`，由 context manager 保证异常路径复位。
- `_backfill_holding_metadata` 的命令层调用若仍必要，显式记录 `commands_holdings → schema` 这一条例外依赖并用只读回归覆盖；若已由 ledger 保证，则在有测试证据后删除防御性重跑，不能直接假定。
- 只有确认全仓和受支持外部入口无消费者后，才删除 `check = cmd_check`；`cache.requests` 在相关测试改 patch `market_quotes.requests` 后再删除。

### 6.4 Phase 3 门禁

每个子阶段分别运行 focused tests 和 `bash scripts/check.sh`。扩展 `tests/test_import_graph.py`，断言：

- 新模块可同时导入且无循环；
- `commands_*.py` 不 import `cache`；
- owner-module monkeypatch 确实穿透到命令行为；
- Phase 0 的临时 DB 隔离与显式只读会话仍有效。

## 7. Phase 4：Evidence 仓迁移（单独授权）

Phase 4 不随 Phase 0-3 自动执行。授权范围必须明确包含：创建 `~/a-stock-agent-evidence`、复制并提交证据、更新本仓引用、删除本仓 247 个 tracked 文件。

执行顺序：

1. 只读盘点 `git ls-files docs/reviews`，生成相对路径、大小和 SHA256 manifest；
2. 将文件复制到独立 evidence 仓，提交后记录 destination commit；
3. 对照 manifest 验证数量、路径和 SHA256 完全一致；验证失败不得删除本仓文件；
4. 本仓 `docs/reviews/README.md` 仅保留 tombstone：源仓最后包含证据的 commit、外部仓位置、destination commit、manifest 路径和恢复命令；不手写 247 行重复索引；
5. 用 `rg -n "docs/reviews/"` 更新当前树中的全部引用，不依赖固定“四个文件”的旧清单；
6. 添加 `.gitignore` 规则，忽略未来 `docs/reviews/*`，但保留 `docs/reviews/README.md`；
7. 最后才删除本仓已验证的 evidence 文件并提交。

回滚：删除提交前可直接停止；删除提交后可从记录的 source commit 恢复 `docs/reviews/`，或从已验证的 evidence commit 按 manifest 复制回来。

Phase 4 不顺带修改 `docs/operations.md` 或 backtest 路径；这些已知文档问题另作小型仓库内修复，避免和跨仓迁移绑定。

**门禁**：外部仓 working tree clean；manifest 校验通过；本仓只剩预期 tombstone；全仓当前文档无悬空 `docs/reviews/` 引用；`bash scripts/check.sh` 通过。

## 8. 验证基线与命令

开工前和每个 Phase 后记录：

```bash
git rev-parse --short HEAD
PYTHONDONTWRITEBYTECODE=1 uv run pytest --collect-only -q -p no:cacheprovider
rg -o '\bassert\b' tests -g '*.py' | wc -l
rg -n 'monkeypatch\.setattr\(cache,' tests
git diff --check
bash scripts/check.sh
```

CLI 契约冒烟必须使用临时数据库：

```bash
export CACHE_DB_PATH="$(mktemp -d)/smoke.db"
uv run a-stock-cache --help
uv run a-stock-cache set-flag 000001 yellow x                 # 期望 3
uv run a-stock-cache set-flag --confirm-write 000001 yellow x # 期望 3
uv run a-stock-cache --bogus set-flag 000001 yellow x         # 期望 2
uv run a-stock-cache bogus                                    # 期望 1
```

测试和重构门禁不得访问或哈希真实生产数据库。

## 9. AGY r2 与 Codex 对抗裁决

| 主张 | 裁决 | 计划处置 |
|---|---|---|
| 无条件生产库硬拦截会破坏正常 CLI | 采纳 | 删除硬拦截和逃生阀，改为测试侧隔离 |
| 生产代码检查 `PYTEST_CURRENT_TEST` | 驳回 | pytest 细节只留在 `tests/conftest.py` |
| 276 处业务测试应全部改走 `main(argv)` | 驳回 | 保留直接单测，以参数化 CLI 契约覆盖入口 |
| `cache.requests` patch 打在空气 | 实测驳回 | 同一模块对象，Phase 2 不删除 |
| Phase 3 会使 46 处 patch 静默失效 | 采纳 | 分 owner 迁移、模块限定调用、行为穿透测试 |
| 用 `cache.__getattr__` 代理 patch | 驳回 | 不能转发对已有模块属性的 setattr |
| 错放 `--confirm-write` 返回 2 | 实测驳回 | 保持现行返回 3；未知前置 flag 才返回 2 |
| Evidence 不应迁出 | 不采纳 | 用户已选择迁出，但改为单独授权和 manifest 门禁 |
| README 手写 247 项 hash 索引 | 驳回 | 使用机器生成 manifest + 小型 tombstone |

## 10. 风险登记与 Go/No-Go

| 风险 | 必须满足的 Go 条件 |
|---|---|
| 测试误写生产数据库 | 无生产守卫/逃生阀；根 fixture 与子进程均解析到临时 DB |
| fetcher 读取触发 schema 写入 | 使用显式只读会话，测试证明不 bootstrap/backfill |
| argparse 改变错误码或消息 | Phase 1 契约矩阵原样通过；错放确认返回 3 |
| `add-holding --notes` 打断调用 | Skill、help、测试及全仓非历史调用同步更新并冒烟 |
| 拆模块后 mock 失效 | 46 处 patch 完成 owner 映射；穿透测试通过 |
| 循环依赖或反向依赖 | import graph 门禁通过，commands 不 import cache |
| Evidence 删除后不可追溯 | 独立授权、外仓 commit、manifest 全匹配、恢复命令验证 |
| 回归难定位 | Phase 0/1/2/3a/3b/3c/4 独立 commit，逐阶段全门禁 |

只有上述条件全部写入实施 diff、focused tests 与阶段证据后，相关 Phase 才是 Go。Phase 0-3 完成不自动触发 Phase 4。
