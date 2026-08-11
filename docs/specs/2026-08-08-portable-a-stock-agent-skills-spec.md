---
title: 可移植 A 股 Agent Skills Suite 迁移规范
status: accepted
implementation_status: completed
created: 2026-08-08
updated: 2026-08-11
closed: 2026-08-11
owner: lin / Hermes
risk_tier: active-layer
---

# 可移植 A 股 Agent Skills Suite 迁移规范

## 1. 请求重写

原始请求：

> 停用 Claude 前，将现有 `a-stock-research`、`a-stock-monitor`、`a-stock-qa` 从 Claude 专属目录迁移为彻底独立、同时兼容 Codex、Claude Code 和 Hermes 的 Skills；不限制实施时间，要求完整方案。

用户澄清（2026-08-11）：Claude 不需要停用。完成条件是 Claude、Codex、Hermes 的全部 `a-stock-*` active Skill 均切换到 `/home/lin/a-stock-agent-skills`，旧 Skill 副本只归档备份。

可执行合同：

> 建立 `/home/lin/a-stock-agent-skills` 作为唯一 canonical 仓库，将三项能力迁移为符合 Agent Skills 开放规范的独立 Skill；将 Research/Monitor 的共享可执行逻辑收敛到仓库内单一 Python runtime，通过稳定 CLI 供三个 Agent 客户端调用，QA 保持纯文本能力；将数据库、日志、锁、凭证和运行产物外置；解除所有 `.claude` 路径、当前工作目录和 sibling Skill 路径依赖；完成确定性测试、三端兼容性验证、生产状态迁移、九个 active Skill 入口切换、旧 Skill 归档和可验证回滚后收口，三个客户端继续保留。

明确含义：

- “独立”指独立于 Claude、Codex、Hermes 的安装目录和工具命名，不指复制第三方依赖或复制共享运行时代码。
- 三个 Skill 是独立的用户能力入口，并作为一个 Suite 发布；Research 和 Monitor 依赖同一个版本化 runtime，纯文本 QA 不依赖 Python runtime。
- `a-stock-lib` 继续是独立共享 Python 包；`a-stock-tracker` 继续是生产数据项目。
- 本规范批准后仍不等于批准修改生产数据库、cron 或 active Skill；这些生产动作保持独立授权边界。

## 2. 目标

1. 建立不归属于任何 Agent 客户端的 A 股投研 Skill 源码仓库。
2. 让 Claude Code、Codex、Hermes 安装和运行相同版本、相同内容的三个 Skill。
3. 保留现有研究框架、数据门禁、持仓账本、监控规则和 QA rubric 的行为语义。
4. 消除 `~/.claude/skills/...`、执行时 `pwd`、sibling Skill 目录和 Skill 内 mutable state 依赖。
5. 让 Hermes 成为生产主入口；Claude Code 和 Codex 保持兼容但不承担生产状态写入。
6. 建立可重复安装、升级、验证、回滚和审计的发布流程。

## 3. 非目标

- 本迁移本身不修改 A/B/C/D/E/F 投资框架、评分阈值、红线或交易判断语义；迁移完成后的投资规则修复须由独立、明确授权的后续规范管理。2026-08-09 的授权修复见 [`2026-08-09-investment-framework-repair-spec.md`](2026-08-09-investment-framework-repair-spec.md)。
- 不证明策略具有样本外收益、Sharpe 或回撤优势。
- 不新增自动下单、券商接口或无人审批的持仓写入。
- 不把 `a-stock-tracker` 改造成 Skill，也不迁移其生产数据管道。
- 不把 `a-stock-lib` 复制进每个 Skill。
- 不在本迁移中重构现有数据库 schema，除非兼容迁移无法完成并重新批准规范。
- 不补写当前不存在的 monitor/tracker QA rubric。
- 不要求不同模型生成逐字一致的自然语言报告。
- 不在验收前删除三个旧仓库或其 Git 历史。

## 4. 当前基线

### 4.1 现有源码

- `/home/lin/.claude/skills/a-stock-research`
- `/home/lin/.claude/skills/a-stock-monitor`
- `/home/lin/.claude/skills/a-stock-qa`
- `/home/lin/a-stock-lib`
- `/home/lin/a-stock-tracker`

三个 Skill 当前分别是独立 Git 仓库；迁移开始前工作树应保持干净并记录 source commit。

### 4.2 已验证测试基线

- `a-stock-lib`：155 passed。
- `a-stock-monitor`：12 passed。
- `a-stock-research`：558 passed，1 failed。
- research 当前失败原因为版本契约漂移：`pyproject.toml=3.2.0`、`SKILL.md=3.2.1`。
- `a-stock-qa` 当前无自动测试，且只存在 research rubric。

### 4.3 已知耦合

- Monitor 直接调用 `~/.claude/skills/a-stock-research/cache.py`。
- Research 和 QA 通过 `~/.claude/skills/a-stock-qa/...` 互相定位。
- `a-stock-lib/scripts/render_prompts.py` 默认读取 Claude Skill 路径，对应测试也断言旧路径。
- `project_paths.py` 默认把 `cache.db` 放在 research Skill 目录。
- cron 脚本包含 research Skill、日志和 tracker `.env` 的绝对路径。
- Agent shell 的当前目录不保证等于 Skill 目录。

### 4.4 生产状态

- 当前数据库使用 SQLite WAL 模式。
- 只读 `PRAGMA integrity_check` 当前返回 `ok`。
- 当前检查时未发现 `cache.db-wal` 或 `cache.db-shm` 文件；迁移时必须重新检查，不能依赖本次快照。
- 持仓、交易事件、分析缓存、L3/Tier 状态属于生产数据。
- 当前存在工作日持仓检查 cron 和 tracker 数据任务。

### 4.5 已落地状态（2026-08-11）

- M0-M6 已完成：canonical runtime、三个 Skill、installer、fixture 和三端 shadow 验证均已提交。
- M7 已完成：生产 DB 通过 SQLite Online Backup API 迁移，`integrity=ok`；Hermes 已作为生产主入口；三端 Skill 入口当前指向同一 canonical release `v0.1.2`。
- 生产配置位于仓库外且权限为 `0600`；cron 只保留一条 canonical 持仓检查任务；受控 Telegram 验证已通过。
- M8 已完成：三端共九个 `a-stock-*` active Skill 均指向 canonical 仓库；原 Claude 三个完整 Skill 和 Hermes 误建副本均保留在仓库外归档；Claude、Codex、Hermes 继续可用。

当前事实证据见 `docs/migration/production-cutover/20260809-115052/`；本节不替代生产状态文件或凭证存储。

## 5. 架构决策

### 5.1 Carrier

唯一 canonical carrier：

```text
/home/lin/a-stock-agent-skills
```

不扩展 `a-stock-lib` 作为 Skill carrier，原因：它是共享确定性 Python 包，不应拥有 Agent prompt、rubric、安装器和客户端发布生命周期。

不扩展 `a-stock-tracker`，原因：它是生产数据项目，其部署、schema 和 cron 生命周期与 Agent Skill 不同。

### 5.2 目标目录

```text
a-stock-agent-skills/
├── README.md
├── AGENTS.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── a_stock_agent_runtime/
│       ├── __init__.py
│       ├── paths.py
│       ├── cache.py
│       ├── fetcher.py
│       ├── checklist.py
│       ├── framework_metadata.py
│       ├── market_quotes.py
│       ├── position_ledger.py
│       ├── schema_ledger.py
│       └── install.py
├── skills/
│   ├── a-stock-research/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   │   └── frameworks/
│   │   ├── assets/
│   │   └── tests/
│   ├── a-stock-monitor/
│   │   ├── SKILL.md
│   │   ├── references/
│   │   └── tests/
│   └── a-stock-qa/
│       ├── SKILL.md
│       ├── references/
│       │   └── rubrics/
│       └── tests/
├── scripts/
│   ├── install.py
│   └── validate.py
├── tests/
│   ├── fixtures/
│   ├── golden/
│   ├── test_installation.py
│   ├── test_portability.py
│   └── test_side_effect_boundaries.py
└── docs/
    ├── specs/
    ├── migration/
    └── reviews/
```

`src/a_stock_agent_runtime` 是 Suite 的内部共享 runtime，不是第四个用户 Skill，也不单独拥有投资规则。

源文件迁移映射至少包括：

```text
a-stock-research/cache.py                  -> src/a_stock_agent_runtime/cache.py
a-stock-research/fetcher.py                -> src/a_stock_agent_runtime/fetcher.py
a-stock-research/checklist.py              -> src/a_stock_agent_runtime/checklist.py
a-stock-research/project_paths.py          -> src/a_stock_agent_runtime/paths.py
a-stock-research/framework_metadata.py     -> src/a_stock_agent_runtime/framework_metadata.py
a-stock-research/market_quotes.py          -> src/a_stock_agent_runtime/market_quotes.py
a-stock-research/position_ledger.py        -> src/a_stock_agent_runtime/position_ledger.py
a-stock-research/schema_ledger.py          -> src/a_stock_agent_runtime/schema_ledger.py
a-stock-research/frameworks/*.md           -> skills/a-stock-research/references/frameworks/*.md
a-stock-qa/rubrics/*.md                    -> skills/a-stock-qa/references/rubrics/*.md
```

实际迁移清单以 tracked-file inventory 和 Python 本地导入图为准；发现未列出的运行依赖时必须补入 provenance 和本节后再实施，不得静默遗漏。

### 5.3 发布单位

- Suite 作为一个 Git 仓库、一个 release/tag 和一个 runtime 版本发布。
- 三个 Skill 各自保留独立 `SKILL.md`、description、references 和触发边界。
- 三个 Skill 不复制 runtime，也不通过 sibling Skill 文件路径调用彼此。
- Skill 文档引用本 Skill 内 references 时，按 Agent Skills 开放规范使用相对于 Skill root 的路径；宿主激活器必须将该路径解析为 Skill root 下的绝对路径，而不是进程 `cwd`。
- 跨 Skill 协同只使用经验证的宿主 Skill discovery/invocation；宿主不支持时显式 `SKIP` 或提示用户单独调用，不新增跨客户端路径解析器。
- Installer 负责安装路径诊断；业务 runtime 和 Skill 不推导其他 Skill 的安装位置。

### 5.4 Python 运行时

新仓库默认使用 Python 3.13+、uv、Ruff、pytest。

Python 3.13 是本机迁移的目标和发布门禁：当前系统 Python、`a-stock-lib` 测试环境及 `tushare==1.4.29` 已在 Python 3.13 上可运行。`baostock` 属于可选 provider，未完成 Python 3.13 安装与导入 smoke 前不得启用；这不允许把主 runtime 无证据降级到旧 Python，也不允许让可选 provider 阻塞默认 TuShare 路径。

根 `pyproject.toml` 暴露稳定入口：

```toml
[project.scripts]
a-stock-cache = "a_stock_agent_runtime.cache:main"
a-stock-fetch = "a_stock_agent_runtime.fetcher:main"
a-stock-install = "a_stock_agent_runtime.install:main"
```

迁移 `cache.py`、`fetcher.py` 和 installer 时，必须把当前顶层 `sys.argv` 解析显式封装为 `main(argv: list[str] | None = None) -> int`。Console script 调用 `main()`；`python -m` 和测试调用同一入口。Checklist 保持内部模块，由既有 `a-stock-cache checklist` 子命令调用，不新增重复的顶层 CLI。现有命令名称、参数、退出码和 JSON/文本输出合同必须保持；本规范明确新增的 W1 `--confirm-write` 是唯一有意的 CLI 合同变化。

M2 必须原子完成包导入迁移：业务模块改用 `a_stock_agent_runtime` 包内导入，测试同步改用包路径和 `paths.py`。最终 release 不保留顶层 `project_paths.py` 兼容 shim；实施中如为保持红绿节奏短暂加入 shim，必须在 M2 验收前删除。`__init__.py` 不得 eager-import 这些存在循环关系的模块。

`a-stock-lib` 以精确版本和 source hash 安装。初始本机 bootstrap 必须显式传入 `--a-stock-lib-source <checkout>` 或 `--a-stock-lib-wheel <wheel>`；installer 在独立 venv 中安装并验证包名、版本、导入和 hash。仓库代码、Skill 文档和默认配置不得硬编码 `/home/lin/a-stock-lib`，也不得在找不到依赖时回退到 `~/a-stock-lib`。长期分发应使用私有包源、Git release 或可校验 wheel；该发布方式不阻塞本机切换。

默认 runtime 安装在 `~/.local/share/a-stock-agent/runtime/<release>/venv`，稳定 console scripts 链接到 `~/.local/bin/`。Installer 必须验证三个命令可由 `PATH` 发现；若 `~/.local/bin` 不在 `PATH` 中则失败并给出一次性修复提示，不允许 Skill 自行猜测 venv 路径。隔离测试通过临时 `HOME` 和 `PATH` 验证同一合同。

`skills/` 是唯一 canonical prompt/Skill 源。自 `a-stock-lib 0.5.0` 起不再保留 prompt fragments、manifest 或 renderer；runtime 与 installer 不得通过 `A_STOCK_LIB_ROOT` 回读外部 prompt 源，三个客户端直接安装本仓库同一份 Skill 内容。

## 6. Agent Skills 兼容合同

### 6.1 Canonical frontmatter

每个 `SKILL.md` 只使用 Agent Skills 开放规范共同字段。Research 和 Monitor 使用：

```yaml
---
name: a-stock-research
description: <包含用途与触发条件的描述>
license: Proprietary
compatibility: Requires local command execution, Python 3.13+, a-stock-agent runtime, a-stock-lib, network access for live research, and configured market-data credentials.
---
```

QA 使用同样的共同字段，但 `compatibility` 只声明读取本 Skill rubric 和接收待检查文本所需能力，不声明 Python、runtime、行情网络或市场数据凭证依赖。

约束：

- `name` 必须与目录名一致。
- 不在 `SKILL.md` 单独维护 release version；版本唯一来源是根 `pyproject.toml` 和 Git tag。
- 不使用 Claude `allowed-tools`、动态命令注入或 Claude 专属 slash 语法。
- 不在 canonical `SKILL.md` 中使用 Hermes 嵌套 metadata 或 Codex 专属配置。
- 不以 `Read`、`WebSearch`、`Bash` 等具体工具名定义行为；使用“读取引用”“检索当前来源”“执行稳定 CLI”等能力级语言。
- 安全规则、写入确认和 fail-closed 边界必须保留在主 `SKILL.md`，不得隐藏到 references。

### 6.2 客户端安装映射

默认目标：

```text
Claude Code: ~/.claude/skills/<skill-name>
Codex:       ~/.agents/skills/<skill-name>
Hermes:      ~/.hermes/skills/research/<skill-name>
```

安装器必须支持：

```text
--client claude|codex|hermes|all
--mode symlink|copy
--source <canonical-repo>
--target-root <override>
--dry-run
--force
--a-stock-lib-source <checkout>
--a-stock-lib-wheel <wheel>
```

规则：

- 首次 bootstrap 入口是仓库内仅使用标准库的 `python3 scripts/install.py`；runtime 安装成功后，`a-stock-install` 必须调用同一实现，不能形成“先安装 runtime 才能运行 installer”的循环依赖。
- Installer 是唯一允许包含 `.claude`、`.agents`、`.hermes` 默认目标映射的客户端 adapter；这些映射不得泄漏到业务 runtime 或 canonical Skill 文档。
- Linux 本机默认 `symlink`，保证单一真源。
- `copy` 模式必须写入 source commit、release version、内容 hash 和安装时间组成的 manifest。
- `--dry-run` 不创建目录、不替换链接、不写 manifest。
- 默认拒绝覆盖普通目录、脏副本、指向未知位置的链接。
- `--force` 仍必须先生成备份并打印回滚路径。
- 安装后必须执行客户端发现验证；不能仅以文件存在判定成功。

## 7. 状态、配置和凭证合同

### 7.1 路径

默认 mutable state：

```text
~/.local/share/a-stock-agent/
├── cache.db
├── logs/
├── locks/
└── artifacts/
```

默认配置：

```text
~/.config/a-stock-agent/runtime.env
```

`paths.py` 在首次需要写入前创建 state/log/lock/artifact 目录，目录权限必须为 0700；只读命令不得仅为查询而创建数据库。配置文件存在时必须是当前用户所有且权限不宽于 0600，否则失败退出。任何路径解析失败都不得回退到旧 `.claude`、tracker 或当前工作目录。

Skill 仓库及三端安装目录不得包含：

- `cache.db`、WAL/SHM；
- 持仓或交易事件导出；
- `.env` 或 token；
- logs、locks、运行报告；
- Agent scratch state；
- pytest、Ruff、Python 缓存。

### 7.2 配置优先级

从高到低：

1. CLI 参数；
2. 当前进程环境变量；
3. 经用户显式配置的 runtime config file；
4. XDG 默认路径。

核心变量：

```text
A_STOCK_STATE_DIR
CACHE_DB_PATH
A_STOCK_LOG_DIR
A_STOCK_LOCK_DIR
A_STOCK_ARTIFACT_DIR
A_STOCK_CONFIG_FILE
A_STOCK_NOTIFY_MODE
TUSHARE_TOKEN
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

`paths.py` 是路径解析的唯一 owner。业务模块不得自行拼接 `.claude`、`.agents`、`.hermes` 或用户 home 下的旧项目路径。

### 7.3 凭证

- 凭证仅通过进程环境或权限为 0600 的外部配置文件提供。
- Installer、测试输出、日志、manifest 和 review evidence 不得打印凭证值。
- `.env.example` 只能包含变量名和说明。
- 缺少实时数据凭证时必须显式降级或失败，不得使用伪造数据填充。
- `A_STOCK_NOTIFY_MODE` 只允许 `disabled` 或 `telegram`，默认 `disabled`；fixture、测试和 shadow 强制为 `disabled`，即使环境中意外存在 Telegram token 也不得发送。
- 迁移后的 cron 只加载 `A_STOCK_CONFIG_FILE` 指定的外部配置；不得继续 source `~/a-stock-tracker/.env` 或其他项目私有配置。

## 8. 运行与副作用合同

### 8.1 命令分类

| 类别 | 示例 | 默认行为 | 审批 |
|---|---|---|---|
| R0 纯读取 | holdings、show-analysis、portfolio-risk | 可直接执行 | 不需要 |
| R1 外部读取/本地缓存 | fetch、研究行情和财报 | 允许网络读取；缓存写入明确标注 | 用户发起研究请求即授权该次读取 |
| W1 本地投资状态写入 | add-holding、sell-holding、dividend、set-analysis、L3/Tier 更新 | 执行前展示命令和影响 | 必须明确确认 |
| E1 外部通知 | Telegram 告警 | 默认关闭于测试/shadow | 生产启用或单次发送需明确授权 |
| E2 真实交易 | 券商下单 | 永不执行 | 本规范禁止 |

### 8.2 写入一致性

- `cache.py` 必须为每个子命令维护唯一的 R0/R1/W1 分类；未分类命令 fail-closed，不能执行。该分类同时驱动帮助文本、Skill 写入提示和测试，避免三处平行名单漂移。
- 所有 W1 CLI 必须要求放在子命令前的全局参数 `--confirm-write`，例如 `a-stock-cache --confirm-write add-holding ...`；缺少该参数时打印拟执行动作和影响、返回退出码 3，且不得打开写事务或改变数据库。Skill 只有在用户确认该具体动作后才可追加此参数。
- Goal 授权项目实施、测试或迁移工具开发，不自动授权生产 W1 投资状态写入；fixture 临时库中的测试写入不属于生产 W1。
- 所有生产状态写入使用同一 `CACHE_DB_PATH`。
- 需要串行化的写命令使用同一锁目录和锁命名规则。
- SQLite 写入使用显式事务、合理 `busy_timeout` 和失败回滚。
- 任何命令不得因为安装在不同 Agent 客户端而拥有不同默认数据库。
- Shadow/fixture 必须使用临时状态目录，不能复用生产 DB、生产 Telegram token 或生产日志。

### 8.3 Fail-closed

以下情况不得生成确定性投资结论：

- 当前行情过期且无法刷新；
- 必需财务字段缺失；
- 数据来源与报告期无法追溯；
- 框架路由不确定；
- L3 状态不可验证；
- QA rubric 不存在；
- 运行时命令失败但模型仍试图补全结果。

允许输出缺口、降级结果和下一步数据需求，但不得把模型推测伪装为已验证事实。

## 9. 功能要求

- **REQ-001 Canonical ownership**：三个 Skill 的唯一可编辑源码位于新仓库，客户端目录只保存链接或可验证安装副本。
- **REQ-002 Host neutrality**：业务 runtime 和 canonical Skill 文档中不存在 `.claude`、`.agents`、`.hermes` 的硬编码路径或客户端专属工具调用；Installer 是唯一例外且只负责客户端目标映射。
- **REQ-003 Runtime ownership**：cache、fetcher 和内部 checklist 逻辑由仓库内单一 runtime 提供；对外只保留 `a-stock-cache`、`a-stock-fetch`、`a-stock-install` 三个稳定 CLI。
- **REQ-004 Skill independence**：Monitor 不依赖 Research Skill 的文件路径；QA 不依赖 Claude 安装路径；Research 不通过硬编码 sibling 路径定位 QA。
- **REQ-005 State isolation**：所有 mutable state 和凭证位于仓库及 Skill 安装目录之外。
- **REQ-006 Behavioral preservation**：迁移不改变现有框架、评分、红线、持仓账本和数据门禁语义。
- **REQ-007 Safe writes**：持仓、交易、分红、分析和 L3/Tier 写入保持明确审批和事务边界。
- **REQ-008 Installation**：同一 release 可安装到 Claude Code、Codex、Hermes，并支持 dry-run、验证和回滚；稳定 CLI 从任意 cwd 均可通过 `PATH` 发现。
- **REQ-009 Data migration**：生产 SQLite 数据通过一致快照迁移，验证 integrity、schema、关键表计数和关键记录抽样。
- **REQ-010 Cron migration**：cron 只调用稳定 CLI 和外置配置，不引用 Skill 安装路径。
- **REQ-011 QA scope honesty**：QA 只宣称支持已有 research rubric；缺 rubric 返回 `SKIP`。
- **REQ-012 Evidence**：每阶段保存命令、退出码、diff、测试和 reviewer verdict，不以 Agent 自述替代验证。
- **REQ-013 Primary host**：生产切换后 Hermes 是主交互入口；Claude Code 与 Codex 默认只读或 shadow，除非另行授权。
- **REQ-014 Reproducibility**：新环境在显式提供可校验的 `a-stock-lib` source checkout 或 wheel 后，能够通过 README 中一条受支持安装路径完成 runtime、三个 Skill 和 fixture 验证；不得依赖隐式 home 路径。
- **REQ-015 Source provenance**：保留三个源仓库 commit、文件清单、迁移映射和被排除状态文件清单。

## 10. 数据迁移合同

### 10.1 前置条件

- 记录旧数据库路径、大小、schema version、journal mode 和关键表计数。
- 暂停所有可能访问该 DB 的 cron、Agent 会话和后台进程。
- 证明没有预期外 writer；无法证明时停止迁移。
- 备份原 DB、相关 WAL/SHM（若存在）和当前 crontab。

### 10.2 一致快照

- 使用 Python `sqlite3.Connection.backup` 或同等 SQLite Online Backup API。
- 不允许只复制主 `cache.db` 文件作为迁移手段。
- WAL checkpoint 可以在无活跃 writer 且锁可控时作为维护步骤，但不是替代 Backup API 的充分条件。

### 10.3 验证

目标 DB 必须满足：

```text
PRAGMA integrity_check = ok
user_version 与源一致
关键表集合一致
holdings 行数一致
交易事件行数一致
analysis_results 行数一致
每个持仓关键字段抽样一致
```

源、目标 DB 验证期间均不得执行生产写入。

### 10.4 切换

- runtime 先在目标 DB 的副本上执行只读 smoke。
- 再执行一条隔离写入 fixture，不使用生产 DB。
- 生产配置切到新 DB 后，先执行只读查询和持仓摘要。
- 只有验证通过才恢复 cron。
- 源 DB 保持只读回滚，不立即删除。

## 11. 测试与验证要求

### 11.1 确定性测试

必须迁入并维持：

- Research 现有全部 pytest；
- Monitor 现有全部 pytest；
- `a-stock-lib` 消费者兼容测试；
- QA 最小自动测试：完整 research 报告、缺关键步骤报告、未知 rubric 三类。

新增最少测试：

1. 三客户端 target path 映射；
2. symlink 和 copy manifest；
3. dry-run 无写入；
4. 未知普通目录拒绝覆盖；
5. CLI 在任意 `cwd` 下可运行；
6. 运行时无 `.claude/.agents/.hermes` 路径；
7. 默认 state 位于 XDG 目录；
8. fixture 不访问生产 DB 和 Telegram；
9. monitor 不读取 research Skill 文件；
10. renderer 接受显式 Skill source；
11. 缺凭证和过期数据 fail-closed；
12. 并发 writer 的锁与事务回滚；
13. 所有 runtime 模块可从安装包导入，且三个公开 CLI 的 `main(argv) -> int` 可直接调用；
14. runtime 安装位置、`~/.local/bin` 链接和任意 cwd/PATH 发现合同；
15. 相对 reference 在三端均按 Skill root 而非进程 cwd 解析；
16. state/config 权限、目录创建和“禁止旧路径回退”；
17. `A_STOCK_NOTIFY_MODE=disabled` 在存在伪造 Telegram token 时仍不发送；
18. QA 在未安装 Python runtime 和市场数据依赖时仍可被发现并执行 rubric 检查。

### 11.2 Golden fixtures

至少保留：

- 每个 A/B/C/D/E/F 框架一个可确定路由 fixture；
- 一个正常完整 research evidence packet；
- 一个过期行情案例；
- 一个缺关键财务字段案例；
- 一个 holdings + L3 只读 monitor 案例；
- 一个 QA compliant 案例；
- 一个 QA non-compliant 案例；
- 一个 unknown rubric `SKIP` 案例。

Golden master 比较确定性结构和安全不变量，不比较整段自然语言。

### 11.3 三端验证

Claude Code、Codex、Hermes 每端都必须完成：

1. Skill discovery；
2. 显式 Skill invocation；
3. 正常 fixture；
4. fail-closed fixture；
5. 任意 cwd 下调用 CLI；
6. 无生产 DB/Telegram 副作用证明。

Hermes 额外完成生产候选 smoke；Claude Code 和 Codex 的验证使用隔离状态。

### 11.4 Review gates

- Spec 批准前：一次独立工程可实施性审查。
- 每个实施阶段完成后：Codex 只读审查该阶段 diff；Hermes 复核每项 finding 后再修复。
- 生产 DB/cron 切换前：单独检查数据迁移证据和回滚命令。
- 最终切换前：聚焦复审 canonical ownership、路径、状态隔离、写入审批和 fail-closed。
- Reviewer 自述不构成通过；父级必须检查 diff、测试和实际客户端发现结果。

这些 review gate 是 Goal 内自动执行的质量检查，不是新的用户审批点。Finding 可在已授权范围内直接修复并重验；只有触及下节列出的授权边界时才暂停 Goal 请求用户决定。

### 11.5 Goal 驱动与最小审批

- 用户批准开始实施时创建一个持续 Goal，默认覆盖 M0-M6：仓库内修改、测试、依赖同步、临时环境、可回滚 Installer 验证，以及在先备份后对三个客户端 Skill 入口进行 shadow 安装；不得为每个里程碑重复请求用户批准。
- 同一 Goal 使用会话内计划记录阶段状态；不为每阶段创建新的 Goal。上下文压缩、自动续跑和非阻塞测试失败不终止 Goal。
- Goal 内允许安全、可逆且属于确认范围的修复和重验；平台自身的文件系统、网络或命令权限提示不视为新的项目审批，但必须遵守平台要求。
- 只有以下边界需要暂停并请求一次明确授权：生产 DB/配置/cron/Telegram/active Skill 切换（M7）；发现必须改变投资规则、数据库 schema、自动交易或其他已确认非目标。
- M7 的生产动作应合并为一次 cutover 审批，明确列出备份、暂停 writer、DB 迁移、active Skill 切换、cron 切换、smoke 和失败回滚，不把这些步骤拆成多次批准。
- M8 只核验九个 active Skill 的 canonical 指向和旧 Skill 归档，不停用任何客户端。

## 12. 验收标准

- **AC-001 / REQ-001**：三个客户端安装目录中的 Skill 内容可追溯到同一 release commit；不存在未声明分叉。
- **AC-002 / REQ-002**：业务 runtime 和 active Skill 文档扫描不含 `.claude/skills`、`.agents/skills` 或 `.hermes/skills` 硬编码路径；Installer 的三客户端目标映射是唯一允许命中项。
- **AC-003 / REQ-003/004/008**：从随机临时 cwd 通过 `PATH` 执行 `a-stock-cache --help`、`a-stock-fetch --help`、`a-stock-install --help` 成功，并用隔离 fixture 执行 `a-stock-cache checklist <代码> <框架>`；三个公开 CLI 的 `main(argv)` 返回整数退出码；Monitor 不读取 Research Skill 文件。
- **AC-004 / REQ-005**：仓库和三端 Skill 安装目录中不存在 DB、WAL、SHM、日志、锁、token 或运行报告。
- **AC-005 / REQ-006**：迁移前后 golden fixture 的框架路由、硬评分、红线、数据缺口和结构化状态一致；任何有意变化必须先更新本规范。
- **AC-006 / REQ-007**：每个 `a-stock-cache` 子命令均有且只有一个 R0/R1/W1 分类；所有 W1 CLI 缺少前置全局参数 `--confirm-write` 时返回 3 且数据库未改变，提供参数后才可在已获用户确认的具体动作或隔离 fixture 中执行。
- **AC-007 / REQ-008**：Installer `--dry-run` 单独证明无文件 diff；随后以 `symlink` 和 `copy` 模式分别正式安装，三端都能发现并显式调用 Skill；回滚恢复原入口。
- **AC-008 / REQ-009**：目标 DB integrity 为 `ok`，schema/user_version 和关键表计数符合迁移记录，关键持仓抽样一致。
- **AC-009 / REQ-010**：crontab 和被调用脚本不含旧 Skill 路径；一次隔离 dry-run 不发送 Telegram；生产恢复后首个确定性检查退出码为 0。
- **AC-010 / REQ-011**：Research rubric 正常评估；未知 monitor/tracker rubric 返回 `SKIP`。
- **AC-011 / REQ-012**：每阶段 evidence 目录包含 prompt、stdout、stderr、exit code、before/after hashes 和 drift 状态。
- **AC-012 / REQ-013**：Hermes 完成真实生产候选 smoke；证据证明 Hermes 识别 canonical Skill、调用已安装 runtime CLI，且运行日志无 `.claude/skills` 路径或 Claude CLI 依赖。
- **AC-013 / REQ-014**：在隔离临时 HOME 中，显式传入 `--a-stock-lib-source <checkout>` 或 `--a-stock-lib-wheel <wheel>`，按 README 完成 runtime、三个 Skill 和 fixture 测试；除该显式输入外不依赖开发者 home 路径。
- **AC-014 / REQ-015**：`docs/migration/source-provenance.md` 记录三个源 commit、迁移映射和排除项。
- **AC-015**：Research、Monitor、QA、runtime 和 `a-stock-lib` 相关测试全部通过，且没有被跳过的迁移关键测试；QA 的独立发现/执行测试不安装 runtime。

## 13. 里程碑与方案

### M0：规范与证据冻结

结果：批准本规范；记录源 commit、测试基线、DB/cron 只读快照和既有审查结论。用户授权开始实施后，本阶段与 M1-M6 共用一个持续 Goal，不单独审批。

非范围：不修改 active Skill、DB、cron 或 Agent 配置。

### M1：Canonical 仓库建立

结果：用每个源仓库的 tracked files 建立新仓库；写入 provenance；排除 mutable/scratch 文件。

验证：源文件清单映射、Git 状态、秘密扫描、排除项检查。

### M2：Runtime 与稳定 CLI

结果：把 cache、fetcher、checklist、paths、framework metadata、market quotes、position ledger、schema ledger 迁入单一 runtime；原子更新包内导入和测试导入；注册三个公开 console scripts；保留 `a-stock-cache checklist`；保持命令合同并加入 W1 明确确认门禁；修复 renderer 的 Skill source 合同。

验证：现有单元测试迁入并全绿；随机 cwd CLI 测试；Codex 阶段审查。

### M3：三项 Skill 标准化

结果：三个 `SKILL.md` 使用共同规范；按显式映射迁移 frameworks/rubrics；同 Skill references 按 Skill root 相对化；跨 Skill 使用宿主 discovery/invocation；QA 保持无 runtime 依赖；安全规则留在主 Skill；解除跨 Skill 路径。

验证：Agent Skills 格式、路径扫描、QA scope 测试、Codex 阶段审查。

### M4：Installer 与隔离环境

结果：支持三客户端 symlink/copy/dry-run/rollback；runtime 使用 uv 安装到版本化用户目录并通过 `~/.local/bin` 暴露稳定 CLI；在临时 HOME 验证。

验证：安装矩阵和漂移 manifest；Codex 阶段审查。

### M5：状态外置与迁移工具

结果：`paths.py` 成为唯一 owner；提供 SQLite backup/verify 命令；所有 fixture 使用隔离状态。

验证：DB 备份测试、完整性/计数验证、失败回滚、无 Telegram 副作用；Codex 阶段审查。

### M6：三端 Shadow

结果：三个客户端对同一正常和边界 fixtures 完成发现、调用和不变量验证；shadow 安装属于 M0-M6 Goal 的一次性实施授权，不逐客户端重复审批。

验证：每端 evidence packet；不访问生产状态；父级核验。

### M7：生产切换

结果：备份并迁移生产 DB；更新 cron；Hermes 作为主入口完成生产候选 smoke；Claude/Codex 保持只读兼容。

验证：DB/cron/Telegram/进程证据；用户单独批准后执行。

### M8：Canonical 收口与旧 Skill 归档

结果：Claude、Codex、Hermes 的九个 active Skill 入口统一指向 canonical 仓库；被替代的旧 Skill 仅归档备份，Claude 保持可用。

验证：九个 symlink 目标一致、三个原 Claude Skill 完整归档、Hermes 误建副本归档、installer rollback manifest 可读。删除任何归档不属于本里程碑，需另行批准。

## 14. 回滚

### 14.1 代码和 Skill 安装

- 保留每个客户端原目录的时间戳备份。
- Installer 必须生成 machine-readable uninstall/rollback manifest。
- 回滚只恢复链接/目录和 runtime 版本，不覆盖生产 DB。

### 14.2 数据

- 保留迁移前源 DB 只读快照。
- 若新 runtime 未产生生产写入，可直接恢复旧 `CACHE_DB_PATH`。
- 若新 runtime 已产生生产写入，禁止简单切回旧 DB；必须停止写入并执行有审计的反向迁移或人工 reconciliation。

### 14.3 Cron 和 Telegram

- 保存完整旧 crontab 和脚本 hash。
- 切换失败时先停新任务，再恢复旧路径；不得让新旧 cron 同时启用。
- Telegram smoke 默认阻断发送；生产通知恢复必须单独验证目标 chat 和消息内容。

## 15. 停止条件

出现以下任一情况立即停止当前阶段：

- 发现 token、chat ID 或其他凭证进入 Git/diff/log；
- 源或目标 DB integrity 非 `ok`；
- 关键表计数或持仓抽样无法解释；
- 迁移期间发现未识别 writer；
- 新旧 cron 可能双重运行；
- 确定性测试出现无法归因的回归；
- fail-closed 变为 fail-open；
- 三端安装内容不再对应同一 release；
- Reviewer 或 Agent 意外修改范围外 active files；
- 实施要求改变投资规则、数据库 schema 或审批边界而规范未更新；
- 无法证明测试没有发送生产 Telegram 消息。

## 16. 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| Monitor 隐式依赖 Research 路径 | 高 | 单一 runtime CLI，禁止 sibling 文件调用 |
| Installer 客户端路径与 host-neutral 扫描冲突 | 中 | 只允许 Installer adapter 持有三端映射，业务 runtime/Skill 保持中立 |
| runtime 已安装但 CLI 不在 PATH | 高 | 版本化 venv + `~/.local/bin` 稳定链接 + 安装后发现验证 |
| W1 审批只停留在 prompt | 高 | CLI 强制 `--confirm-write`，缺参返回 3 且零写入 |
| DB/WAL 迁移丢数据 | 高 | 暂停 writer、Online Backup API、integrity/计数/抽样 |
| cron 双跑或漏跑 | 高 | 备份、暂停、单点切换、恢复后验证 |
| 测试误发 Telegram | 高 | 隔离 env、发送 stub、生产 token 不注入 |
| 三端模型行为差异 | 中 | 比较确定性不变量，不比较完整自然语言 |
| symlink 不被某客户端发现 | 中 | 实测发现；失败时 copy+hash manifest |
| `a-stock-lib` 安装不可重现 | 中 | 固定版本，记录 source/wheel hash，后续包源化 |
| Git archive 丢失历史 | 低 | provenance + 保留旧仓库只读；不为历史引入 subtree 复杂度 |
| QA 覆盖被夸大 | 中 | 只声明已有 research rubric，缺失返回 SKIP |
| Prompt 拆分改变语义 | 中 | 先迁移行为再 slimming；golden fixture 和阶段审查 |

## 17. 方案中明确后置的工作

- 将 `a-stock-lib` 发布到稳定私有包源；本机可复现安装通过后再做。
- 将过长 Research `SKILL.md` 按 progressive disclosure 拆分；必须在行为基线建立后进行。
- 新增 monitor/tracker QA rubric；需独立领域规范和验收。
- 投资效果回测和样本外验证；属于策略可信性项目，不属于平台迁移。
- 删除或合并旧 Git 仓库；稳定期和回滚窗口结束后另行批准。

## 18. 规范变更规则

以下变化必须先修改本规范并重新审批：

- 投资框架、评分或红线改变；
- 数据库 schema 改变；
- 自动写入或外部通知审批边界改变；
- 新增自动交易；
- 改变 canonical carrier；
- 允许不同客户端维护独立 Skill 副本；
- 取消生产 DB/cron 回滚能力。

不改变行为的文档措辞、测试补充和 lint 修复可以在当前规范内完成。

## 19. 审批状态

- Spec approval：accepted for implementation
- M0-M6 Goal execution approval：completed（一次批准覆盖非生产实施、验证和可回滚 shadow 安装，不逐阶段重复）
- Canonical 仓库创建及源码迁移：completed
- 三端 shadow Skill 安装：包含在 M0-M6 Goal 授权中，执行前自动备份
- M7 production cutover：completed 2026-08-09（一次审批合并生产 DB、配置、active Skill、cron、Hermes smoke 和回滚步骤；证据见 `docs/migration/production-cutover/20260809-115052/`）
- M8 canonical 收口与旧 Skill 归档：completed 2026-08-11；Claude、Codex、Hermes 均保留
- Implementation closeout：completed 2026-08-11；全部验收条件已满足，无遗留迁移里程碑

本规范已实施并结案，继续作为当前架构、安全边界和变更规则的基线。后续新增功能、投资规则、数据库 schema 或生产自动化变更不属于本次迁移，应按第 18 节重新审批。
