---
title: 可移植 A 股 Agent Skills Suite 实施计划
status: in_progress
created: 2026-08-08
updated: 2026-08-09
spec: /home/lin/a-stock-agent-skills/docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md
spec_alignment: reviewed
execution_authorized: true
risk_tier: active-layer
---

# 可移植 A 股 Agent Skills Suite 实施计划

> 本计划精确到文件、命令、验证和回滚，但不构成实施授权。用户一次明确要求“按 Spec 开始实施”即授权一个持续 Goal 执行 M0-M6；M7 生产切换仍需一次单独明确批准，M8 仅在未被 M7 带条件授权覆盖时单独确认。

> 执行记录（2026-08-09）：M0-M6 已完成并提交；Claude 登录恢复后，按修正后的参数顺序在临时 shadow 完成 research/stale/monitor/QA 四个 smoke，全部 exit 0。Codex、Hermes、Claude 三端四组确定性 invariant 比较全部通过；Claude auth 的 mtime/hash 未变，临时 shadow 已清理。AGY 对 M0-M6 的分段复审发现 renderer 未配置时的哨兵值和 QA compliant 夹具证据不足，已分别改为显式 `None` 并补齐合规夹具，三端 QA 复跑均为 `COMPLIANT`。M7 已按用户一次性 cutover 请求完成：生产 DB 通过 Online Backup API 迁移并完成 integrity/schema/关键计数/holdings 摘要核验；runtime.env 设为 0600；三端切到 release `0.1.0-48a82c85b367`；Hermes 候选 smoke、CLI/cron 禁通知 smoke、受控 Telegram 验证（HTTP 200）全部通过；cron after 仅替换持仓检查任务，rollback manifest 保留。详见 `docs/reviews/client-shadow-20260808-claude/`、`docs/reviews/client-shadow-20260808-retry/`、`docs/reviews/agy-m0m6-fix-20260809/` 与 `docs/migration/production-cutover/20260809-115052/`。M8 Claude 停用仍未授权。

## 0. Minimum landing change

首个最小落地不是迁数据库或安装 active Skill，而是：

1. 初始化 `/home/lin/a-stock-agent-skills` Git 仓库；
2. 保存三个源仓库 commit、tracked-file 清单和排除清单；
3. 经临时目录提取非 mutable 源文件到新仓库目标目录；
4. 运行秘密/状态文件扫描；
5. 提交 M1 canonical skeleton；
6. Codex 只读审查该提交。

M1 不修改：

- `~/.claude/skills/a-stock-*`；
- `/home/lin/a-stock-lib`；
- `/home/lin/a-stock-tracker`；
- `~/.hermes/skills`、`~/.agents/skills`、`~/.claude/skills` 安装入口；
- 生产 `cache.db`、cron、Telegram 和 gateway。

## 1. 全局路径与执行约定

所有实施 shell 使用以下变量，禁止在源码中写死这些值：

```bash
export SUITE=/home/lin/a-stock-agent-skills
export SRC_RESEARCH=/home/lin/.claude/skills/a-stock-research
export SRC_MONITOR=/home/lin/.claude/skills/a-stock-monitor
export SRC_QA=/home/lin/.claude/skills/a-stock-qa
export A_STOCK_LIB_SOURCE=/home/lin/a-stock-lib
export TRACKER=/home/lin/a-stock-tracker
export SPEC="$SUITE/docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md"
```

执行规则：

- 不使用系统 Python `--break-system-packages`；所有项目执行通过 uv venv。
- 不复制 `.env`、DB、WAL/SHM、logs、locks、`.claude`、memory、AI review scratch。
- 每阶段实现后顺序为：测试 → diff/status → Codex 只读审查 → 父级复核 → 最小修复 → 重跑相关测试 → commit。
- Reviewer 自述不能替代本计划列出的命令和退出码。
- 每阶段 evidence 保存到 `docs/reviews/m<stage>-<run-id>/`，至少包含 review prompt、stdout、stderr、exit code、before/after source hash 和 drift 状态；凭证、DB 与运行状态文件不得进入 evidence。
- M0-M6 共用一个持续 Goal；阶段 review gate 是 Goal 内质量检查，不是新的用户审批点。
- Goal 内允许仓库修改、依赖同步、临时环境、测试、可回滚 installer 验证，以及隔离的三端 shadow 安装（非空临时 target 先备份）；不逐阶段或逐客户端重复请求批准。
- 生产 DB、配置、cron、Telegram 和 Hermes 主入口切换只在 M7 一次性 cutover 批准后执行；Claude 停用按 M8 边界处理。

## 2. 阶段账本

| 阶段 | 结果 | 初始状态 | Goal / 审批边界 |
|---|---|---|---|
| M0 | Spec、来源、基线冻结 | completed | M0-M6 持续 Goal |
| M1 | Canonical 仓库和 provenance | completed | M0-M6 持续 Goal |
| M2 | Runtime、CLI、renderer | completed | M0-M6 持续 Goal |
| M3 | 三个标准 Skill | completed | M0-M6 持续 Goal |
| M4 | Installer、三端隔离安装 | completed | M0-M6 持续 Goal；仅临时 target |
| M5 | 状态外置和迁移工具 | completed | M0-M6 持续 Goal；仅 fixture |
| M6 | 三端 shadow | completed | M0-M6 持续 Goal；三端四个 fixture smoke 与 invariant 比较完成 |
| M7 | 生产 DB、配置、cron、Telegram、Hermes 切换 | completed | 2026-08-09 cutover evidence；rollback manifest 保留 |
| M8 | 稳定、回滚演练、Claude 停用 | not_started | 未被 M7 带条件授权覆盖时单独确认 |

---

# M0：冻结规范与现状

## Task M0.1：确认 Spec 和审查证据

**读取：**

- `$SPEC`
- `$SUITE/docs/reviews/20260808-001550-agy-spec-r1/`
- `$SUITE/docs/reviews/20260808-002319-agy-spec-r2/`

**命令：**

```bash
sha256sum "$SPEC"
find "$SUITE/docs/reviews/20260808-001550-agy-spec-r1" -maxdepth 1 -type f -printf '%f\n' | sort
find "$SUITE/docs/reviews/20260808-002319-agy-spec-r2" -maxdepth 1 -type f -printf '%f\n' | sort
sed -n '1,100p' "$SUITE/docs/reviews/20260808-002319-agy-spec-r2/agy_stdout.txt"
```

**通过：**

- 记录当前 Spec hash 和状态；
- R1/R2 证据保留为历史输入，不把旧 hash 当作现行 Spec 的通过条件；
- 用户启动 M0-M6 Goal 时，以当时确认的 Spec 内容为执行基线。

**停止：** Goal 启动后发现 Spec 有改变投资规则、schema、自动交易或审批边界的未批准变化。

## Task M0.2：记录源仓库和生产只读基线

**创建：**

- `$SUITE/docs/migration/source-provenance.md`
- `$SUITE/docs/migration/source-files-research.txt`
- `$SUITE/docs/migration/source-files-monitor.txt`
- `$SUITE/docs/migration/source-files-qa.txt`
- `$SUITE/docs/migration/baseline-tests.md`
- `$SUITE/docs/migration/excluded-files.md`

**命令：**

```bash
for repo in "$SRC_RESEARCH" "$SRC_MONITOR" "$SRC_QA" "$A_STOCK_LIB_SOURCE" "$TRACKER"; do
  git -C "$repo" status --short
  git -C "$repo" rev-parse HEAD
  git -C "$repo" log -1 --format='%H %cI %s'
done

git -C "$SRC_RESEARCH" ls-files | sort > "$SUITE/docs/migration/source-files-research.txt"
git -C "$SRC_MONITOR" ls-files | sort > "$SUITE/docs/migration/source-files-monitor.txt"
git -C "$SRC_QA" ls-files | sort > "$SUITE/docs/migration/source-files-qa.txt"
```

生产 DB、cron 只读证据只记录命令输出，不打开 SQLite 读连接：

```bash
stat -c '%n %s %y' "$SRC_RESEARCH/cache.db"
find "$SRC_RESEARCH" -maxdepth 1 -type f \( -name 'cache.db-wal' -o -name 'cache.db-shm' \) -printf '%f %s\n'
crontab -l
```

**说明：** SQLite `mode=ro` 连接在 WAL 模式下仍可能创建 `-shm/-wal` sidecar，因此 M0 不用数据库连接做“只读”基线。DB 内容检查留到获批的 M7 维护窗口。

**通过：** 五个源仓库工作树干净；若不干净则列出并由用户决定，不自动清理。

---

# M1：建立 Canonical 仓库

## Task M1.1：初始化仓库和基础配置

**创建：**

- `$SUITE/.git/`
- `$SUITE/.gitignore`
- `$SUITE/README.md`
- `$SUITE/AGENTS.md`
- `$SUITE/docs/migration/README.md`

**命令：**

```bash
cd "$SUITE"
git init -b main
```

`.gitignore` 必须至少包含：

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.py[cod]
*.db
*.db-wal
*.db-shm
.env
runtime.env
logs/
locks/
artifacts/
.claude/
ai-collab/
```

`AGENTS.md` 只保存本仓库开发/验证规则，不复制 Claude 专属命令和个人 memory。

**验证：**

```bash
git -C "$SUITE" status --short
git -C "$SUITE" check-ignore -v .probe/cache.db
```

## Task M1.2：提取 Research tracked source

**目标文件：**

```text
src/a_stock_agent_runtime/{cache,fetcher,checklist,paths,framework_metadata,market_quotes,position_ledger,schema_ledger}.py
skills/a-stock-research/SKILL.md
skills/a-stock-research/references/frameworks/*.md
scripts/check-holdings-cron.sh
tests/research/
docs/migration/source-research-changelog.md
```

**提取命令：**

```bash
RESEARCH_STAGE=$(mktemp -d)

git -C "$SRC_RESEARCH" archive HEAD -- \
  cache.py fetcher.py checklist.py project_paths.py \
  framework_metadata.py market_quotes.py position_ledger.py schema_ledger.py \
  SKILL.md frameworks tests check-holdings-cron.sh docs/CHANGELOG.md \
  | tar -x -C "$RESEARCH_STAGE"

mkdir -p "$SUITE/src/a_stock_agent_runtime" \
         "$SUITE/skills/a-stock-research/references/frameworks" \
         "$SUITE/scripts" "$SUITE/tests/research"

cp "$RESEARCH_STAGE/cache.py" "$SUITE/src/a_stock_agent_runtime/cache.py"
cp "$RESEARCH_STAGE/fetcher.py" "$SUITE/src/a_stock_agent_runtime/fetcher.py"
cp "$RESEARCH_STAGE/checklist.py" "$SUITE/src/a_stock_agent_runtime/checklist.py"
cp "$RESEARCH_STAGE/project_paths.py" "$SUITE/src/a_stock_agent_runtime/paths.py"
cp "$RESEARCH_STAGE/framework_metadata.py" "$SUITE/src/a_stock_agent_runtime/framework_metadata.py"
cp "$RESEARCH_STAGE/market_quotes.py" "$SUITE/src/a_stock_agent_runtime/market_quotes.py"
cp "$RESEARCH_STAGE/position_ledger.py" "$SUITE/src/a_stock_agent_runtime/position_ledger.py"
cp "$RESEARCH_STAGE/schema_ledger.py" "$SUITE/src/a_stock_agent_runtime/schema_ledger.py"
cp "$RESEARCH_STAGE/SKILL.md" "$SUITE/skills/a-stock-research/SKILL.md"
cp -a "$RESEARCH_STAGE/frameworks/." "$SUITE/skills/a-stock-research/references/frameworks/"
cp -a "$RESEARCH_STAGE/tests/." "$SUITE/tests/research/"
cp "$RESEARCH_STAGE/check-holdings-cron.sh" "$SUITE/scripts/check-holdings-cron.sh"
cp "$RESEARCH_STAGE/docs/CHANGELOG.md" "$SUITE/docs/migration/source-research-changelog.md"
```

## Task M1.3：提取 Monitor 和 QA tracked source

**目标文件：**

```text
skills/a-stock-monitor/{SKILL.md,CHANGELOG.md,references/,scripts/policy_replay.py}
tests/monitor/
skills/a-stock-qa/{SKILL.md,README.md,references/rubrics/}
docs/migration/source-qa-specs/
```

**命令：**

```bash
MONITOR_STAGE=$(mktemp -d)
QA_STAGE=$(mktemp -d)

git -C "$SRC_MONITOR" archive HEAD -- SKILL.md CHANGELOG.md references tools tests \
  | tar -x -C "$MONITOR_STAGE"
git -C "$SRC_QA" archive HEAD -- SKILL.md README.md rubrics docs/specs \
  | tar -x -C "$QA_STAGE"

mkdir -p "$SUITE/skills/a-stock-monitor/scripts" \
         "$SUITE/skills/a-stock-monitor/references" \
         "$SUITE/tests/monitor" \
         "$SUITE/skills/a-stock-qa/references/rubrics" \
         "$SUITE/docs/migration/source-qa-specs"

cp "$MONITOR_STAGE/SKILL.md" "$SUITE/skills/a-stock-monitor/SKILL.md"
cp "$MONITOR_STAGE/CHANGELOG.md" "$SUITE/skills/a-stock-monitor/CHANGELOG.md"
cp -a "$MONITOR_STAGE/references/." "$SUITE/skills/a-stock-monitor/references/"
cp "$MONITOR_STAGE/tools/policy_replay.py" "$SUITE/skills/a-stock-monitor/scripts/policy_replay.py"
cp -a "$MONITOR_STAGE/tests/." "$SUITE/tests/monitor/"

cp "$QA_STAGE/SKILL.md" "$SUITE/skills/a-stock-qa/SKILL.md"
cp "$QA_STAGE/README.md" "$SUITE/skills/a-stock-qa/README.md"
cp -a "$QA_STAGE/rubrics/." "$SUITE/skills/a-stock-qa/references/rubrics/"
cp -a "$QA_STAGE/docs/specs/." "$SUITE/docs/migration/source-qa-specs/"
```

**验证：**

```bash
find "$SUITE" -path '*/.git' -prune -o -type f -print | sort
find "$SUITE" -type f \( -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '.env' \) -print
rg -n --hidden --glob '!.git/**' 'TELEGRAM_BOT_TOKEN=.+|TUSHARE_TOKEN=.+' "$SUITE" || true
```

第二条必须无输出；秘密扫描只允许 `.env.example` 中空值/说明，不允许真实值。

## Task M1.4：提交和阶段审查

```bash
cd "$SUITE"
git add .
git diff --cached --check
git diff --cached --stat
git commit -m 'chore: establish canonical a-stock skill suite'
codex review --commit HEAD
```

父级复核 findings 后，只修 M1 extraction/provenance blocker；不提前重构 runtime。

**M1 回滚：** 删除新仓库中除 `docs/specs`、`docs/reviews` 外的未发布文件，或在已提交时 `git revert HEAD`；不得修改源仓库。

---

# M2：Runtime、CLI 和 a-stock-lib renderer

## Task M2.1：建立 pyproject 和 RED tests

**创建/修改：**

- `$SUITE/pyproject.toml`
- `$SUITE/src/a_stock_agent_runtime/__init__.py`
- `$SUITE/src/a_stock_agent_runtime/install.py`
- `$SUITE/tests/helpers.py`
- `$SUITE/tests/research/test_*.py`
- `$SUITE/tests/test_cli_contract.py`
- `$SUITE/tests/test_import_graph.py`
- `$SUITE/tests/test_paths.py`
- `$SUITE/tests/test_command_classification.py`

`pyproject.toml` 目标结构：

```toml
[project]
name = "a-stock-agent-skills"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "akshare==1.18.64",
  "pandas==3.0.2",
  "requests==2.33.1",
  "tushare==1.4.29",
]

[project.scripts]
a-stock-cache = "a_stock_agent_runtime.cache:main"
a-stock-fetch = "a_stock_agent_runtime.fetcher:main"
a-stock-install = "a_stock_agent_runtime.install:main"

[dependency-groups]
dev = ["pytest==9.0.3", "ruff==0.11.0", "mypy==1.15.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
target-version = "py313"
```

`a-stock-lib` 暂不通过隐式 sibling source 解析。开发和 bootstrap 必须显式提供 `$A_STOCK_LIB_SOURCE` 构建出的可校验 wheel；installer 验证包名 `a-stock-lib`、版本 `0.4.1`、source commit 和 wheel hash。长期包源化按 Spec 后置，不阻塞本机迁移。

若源测试包含共享 `tests/research/helpers.py`，在修改导入前将其移动为 `tests/helpers.py`，不保留两份副本。

先构建并显式安装本机 `a-stock-lib` wheel，再写 CLI/paths/import/classification tests 并运行 RED：

```bash
cd "$SUITE"
LIB_WHEEL_DIR=$(mktemp -d)
uv build "$A_STOCK_LIB_SOURCE" --out-dir "$LIB_WHEEL_DIR"
uv sync --all-groups
uv pip install --python .venv/bin/python --no-deps "$LIB_WHEEL_DIR"/a_stock_lib-0.4.1-py3-none-any.whl
uv run python -c "import importlib.metadata as m; assert m.version('a-stock-lib') == '0.4.1'"
uv run pytest tests/test_cli_contract.py tests/test_import_graph.py tests/test_paths.py tests/test_command_classification.py -q
```

预期：由于 `main()`、XDG paths 和命令分类尚未完成而失败；记录具体失败，不接受测试意外通过。

## Task M2.2：原子迁移包内导入

**修改：**

- `src/a_stock_agent_runtime/cache.py`
- `src/a_stock_agent_runtime/fetcher.py`
- `src/a_stock_agent_runtime/checklist.py`
- `src/a_stock_agent_runtime/framework_metadata.py`
- `src/a_stock_agent_runtime/market_quotes.py`
- `src/a_stock_agent_runtime/position_ledger.py`
- `src/a_stock_agent_runtime/schema_ledger.py`
- `src/a_stock_agent_runtime/paths.py`
- `tests/research/*.py`

导入替换：

```text
import cache                         -> from a_stock_agent_runtime import cache
import checklist                     -> from a_stock_agent_runtime import checklist
import framework_metadata            -> from a_stock_agent_runtime import framework_metadata
import market_quotes                 -> from a_stock_agent_runtime import market_quotes
from project_paths import X          -> from a_stock_agent_runtime.paths import X
from schema_ledger import X          -> from a_stock_agent_runtime.schema_ledger import X
from position_ledger import X        -> from a_stock_agent_runtime.position_ledger import X
```

测试必须 import 安装包路径；不创建最终 `project_paths.py` shim。`__init__.py` 保持空/只含版本，不 eager import。

**验证：**

```bash
cd "$SUITE"
uv run python - <<'PY'
import a_stock_agent_runtime.cache
import a_stock_agent_runtime.fetcher
import a_stock_agent_runtime.checklist
import a_stock_agent_runtime.framework_metadata
import a_stock_agent_runtime.market_quotes
import a_stock_agent_runtime.position_ledger
import a_stock_agent_runtime.schema_ledger
print('IMPORT_OK')
PY
uv run pytest tests/research -q
```

## Task M2.3：实现 XDG paths、CLI main 和 W1 门禁

**`paths.py` 必须实现：**

- CLI > env > `A_STOCK_CONFIG_FILE` > XDG defaults；
- state/log/lock/artifact 目录写前创建 0700；
- config owner/0600 校验；
- 只读查询不创建 DB；
- 无旧路径或 cwd fallback。

**CLI 必须实现：**

```python
def main(argv: list[str] | None = None) -> int:
    ...
```

`cache.py` 现有 `COMMANDS` dispatch 保留；新增单一命令分类表，保证每个子命令恰好属于 R0、R1 或 W1，未分类命令 fail-closed。该分类同时驱动帮助文本、Skill 写入提示和测试，不维护平行名单。

所有 W1 使用位于子命令前的全局参数 `--confirm-write`：

```text
a-stock-cache --confirm-write add-holding ...
```

缺少参数时打印拟执行动作和影响，返回 `3`，不得打开写事务或改变 DB；提供参数也只表示 CLI 门禁已满足，Skill 仍须先获得用户对该具体动作的确认。Goal 不授权生产 W1，fixture 临时库写入不属于生产 W1。

`main()` 返回整数，不直接在核心分支调用 `sys.exit()`。模块尾部仅：

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

Fetcher 同样处理。Checklist 保持内部模块，只由既有 `a-stock-cache checklist` 子命令调用，不新增顶层 CLI 或独立 `main()`。

**验证：**

```bash
cd "$SUITE"
uv run pytest tests/test_cli_contract.py tests/test_paths.py tests/research -q
TMP_CWD=$(mktemp -d)
(
  cd "$TMP_CWD"
  "$SUITE/.venv/bin/a-stock-cache" --help
  "$SUITE/.venv/bin/a-stock-fetch" --help
  "$SUITE/.venv/bin/a-stock-cache" checklist 000001 A
)
uv run pytest tests/test_command_classification.py tests/test_side_effect_boundaries.py -q
```

分类测试必须枚举 `COMMANDS` 全集；每个 W1 至少验证缺少确认时退出码为 3 且 fixture DB hash 不变。

## Task M2.4：修复 a-stock-lib renderer（独立仓库）

**修改：**

- `/home/lin/a-stock-lib/scripts/render_prompts.py`
- `/home/lin/a-stock-lib/tests/test_render_prompts.py`
- `/home/lin/a-stock-lib/README.md`（若记录调用方式）

**合同：**

- 删除 `/home/lin/.claude/skills/a-stock-research/SKILL.md` 默认常量；
- `--skill-source` 为正常调用必填；
- `A_STOCK_SKILL_SOURCE` 只作显式兼容覆盖；
- 无有效 source 时非零退出；
- 输出不得重新写入 `.claude` 路径。

**验证：**

```bash
cd "$A_STOCK_LIB_SOURCE"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_render_prompts.py -q
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests -q
ruff check scripts/render_prompts.py tests/test_render_prompts.py
codex review --uncommitted
```

父级复核后：

```bash
git add scripts/render_prompts.py tests/test_render_prompts.py README.md
git diff --cached --check
git commit -m 'refactor: make skill source explicit in prompt renderer'
```

如 README 无变化，不得强行 add。

## Task M2.5：Runtime 全量门禁和提交

```bash
cd "$SUITE"
uv lock
uv run ruff check src tests
uv run pytest -q
PYTHONDONTWRITEBYTECODE=1 "$A_STOCK_LIB_SOURCE/.venv/bin/python" -m pytest -p no:cacheprovider "$A_STOCK_LIB_SOURCE/tests" -q
rg -n '/home/lin/\.(claude|agents|hermes)|~/\.(claude|agents|hermes)|\.(claude|agents|hermes)/skills|from project_paths|import project_paths' \
  src/a_stock_agent_runtime tests --glob '!install.py' || true
git diff --check
git status --short
codex review --uncommitted
```

要求路径扫描无运行代码命中；历史 migration docs 命中不属于失败。

修复有效 finding 后：

```bash
git add pyproject.toml uv.lock src tests
git commit -m 'feat: package shared a-stock runtime and stable cli'
```

**M2 回滚：** `git revert <M2-commit>`；a-stock-lib 使用独立 `git revert <renderer-commit>`。两仓库回滚必须成对记录。

---

# M3：标准化三个 Skill

## Task M3.1：Research Skill

**修改：**

- `skills/a-stock-research/SKILL.md`
- `skills/a-stock-research/references/frameworks/*.md`
- 必要时新增 `skills/a-stock-research/references/*.md`

**要求：**

- frontmatter 仅共同字段；移除独立 version；
- Claude 工具名改为能力级语言；
- `python3 ~/.claude/.../cache.py` 改为 `a-stock-cache`；
- `python3 ~/.claude/.../fetcher.py` 改为 `a-stock-fetch`；
- 本 Skill framework 引用使用 `references/frameworks/<file>.md`；
- QA 跨 Skill 只通过经验证的宿主 Skill discovery/invocation；宿主不支持时显式 `SKIP` 或提示用户单独调用；
- 不改变框架、评分、红线和 fail-closed 语义；
- 第一轮不拆分/瘦身长 SKILL.md。

## Task M3.2：Monitor Skill

**修改：**

- `skills/a-stock-monitor/SKILL.md`
- `skills/a-stock-monitor/references/*.md`
- `skills/a-stock-monitor/scripts/policy_replay.py`
- `tests/monitor/*.py`

替换所有 research 文件调用为 `a-stock-cache`/`a-stock-fetch`。Policy replay 保持 Skill bundled script，相对路径按 Skill root。

## Task M3.3：QA Skill 和最小测试

**修改/创建：**

- `skills/a-stock-qa/SKILL.md`
- `skills/a-stock-qa/references/rubrics/a-stock-research.md`
- `tests/qa/test_qa_contract.py`
- `tests/qa/standalone_smoke.py`
- `tests/fixtures/qa/{compliant,non_compliant,unknown_rubric}.md`

**要求：**

- 只声明 research rubric；
- monitor/tracker/未知类型返回 `SKIP`；
- QA 不改报告、不写 DB、不发通知；
- QA 的 frontmatter 不声明 Python、runtime、行情网络或市场数据凭证；
- QA rubric 检查不得 import `a_stock_agent_runtime` 或 `a_stock_lib`。

## Task M3.4：Skill validator

**创建：**

- `scripts/validate.py`
- `tests/test_skill_validation.py`

Validator 至少检查：

- 三个 `SKILL.md` 存在；
- `name` 等于目录名；
- `description` 非空且含 trigger；
- 同 Skill relative references 存在；
- 业务 runtime 和 canonical Skill 无 `.claude/.agents/.hermes` 路径；installer 的三客户端目标映射是唯一例外；
- 无 Claude-only frontmatter/动态注入；
- 安全审批和 fail-closed 规则位于主 Skill；
- 未打包 mutable/secret 文件。

**验证：**

```bash
cd "$SUITE"
uv run python scripts/validate.py
uv run pytest tests/monitor tests/qa tests/test_skill_validation.py -q
env -i HOME="$HOME" PATH="/usr/bin:/bin" python3 -I tests/qa/standalone_smoke.py
uv run pytest -q
uv run ruff check src tests scripts
rg -n '~?/?.*\.claude/skills|~?/?.*\.agents/skills|~?/?.*\.hermes/skills' skills src/a_stock_agent_runtime --glob '!install.py' || true
codex review --uncommitted
```

路径扫描必须无 active 内容命中；QA standalone smoke 必须仅依赖标准库、QA `SKILL.md` 和 research rubric fixture。

```bash
git add skills scripts tests
git commit -m 'feat: standardize portable research monitor and qa skills'
```

**M3 回滚：** `git revert <M3-commit>`；runtime 不回滚。

---

# M4：Installer 和三端隔离安装

## Task M4.1：stdlib bootstrap installer

**修改：**

- `scripts/install.py`
- `src/a_stock_agent_runtime/install.py`
- `tests/test_installation.py`

`scripts/install.py` 只能使用标准库，并调用可共享的实现；在 runtime 未安装时也可执行 `--help`、`--dry-run` 和正式 bootstrap。

支持参数必须与 Spec 一致：

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

**目标映射：**

```text
claude -> $HOME/.claude/skills/<name>
codex  -> $HOME/.agents/skills/<name>
hermes -> $HOME/.hermes/skills/research/<name>
```

**RED：**

```bash
cd "$SUITE"
uv run pytest tests/test_installation.py -q
```

**GREEN/隔离验证：**

```bash
TEST_HOME=$(mktemp -d)
TEST_PATH="$TEST_HOME/.local/bin:/usr/bin:/bin"
HOME="$TEST_HOME" PATH="$TEST_PATH" python3 "$SUITE/scripts/install.py" \
  --client all --mode symlink --source "$SUITE" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE" \
  --target-root "$TEST_HOME" --dry-run
find "$TEST_HOME" -mindepth 1 -print
```

Dry-run 后 `find` 必须无输出。

```bash
HOME="$TEST_HOME" PATH="$TEST_PATH" python3 "$SUITE/scripts/install.py" \
  --client all --mode symlink --source "$SUITE" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE" \
  --target-root "$TEST_HOME"
HOME="$TEST_HOME" PATH="$TEST_PATH" python3 "$SUITE/scripts/validate.py" --installed-root "$TEST_HOME"
```

Copy 模式使用另一个临时 HOME，并验证 manifest/source hash。

Installer 是唯一允许包含上述三客户端默认路径的 adapter。它必须拒绝覆盖普通目录、脏副本和未知链接；`--force` 也必须先备份并输出 rollback manifest。客户端 discovery 验证失败即安装失败，不能仅检查文件存在。

## Task M4.2：版本化 runtime 和稳定 PATH

**修改：**

- `scripts/install.py`
- `src/a_stock_agent_runtime/install.py`
- `tests/test_installation.py`
- `tests/test_portability.py`

默认安装合同：

```text
$HOME/.local/share/a-stock-agent/runtime/<release>/venv
$HOME/.local/bin/a-stock-cache
$HOME/.local/bin/a-stock-fetch
$HOME/.local/bin/a-stock-install
```

Installer 从显式 `--a-stock-lib-source` 构建 wheel，或使用显式 `--a-stock-lib-wheel`；验证包名、版本、source/wheel hash 和 import。它不得回退到 sibling checkout。若稳定 CLI 不能由 `PATH` 发现，则失败并打印一次性修复提示。

**隔离验证：**

```bash
cd "$SUITE"
RUNTIME_HOME=$(mktemp -d)
RUNTIME_PATH="$RUNTIME_HOME/.local/bin:/usr/bin:/bin"
HOME="$RUNTIME_HOME" PATH="$RUNTIME_PATH" python3 scripts/install.py \
  --client all --mode symlink --source "$SUITE" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE"
(
  cd "$(mktemp -d)"
  HOME="$RUNTIME_HOME" PATH="$RUNTIME_PATH" a-stock-cache --help
  HOME="$RUNTIME_HOME" PATH="$RUNTIME_PATH" a-stock-fetch --help
  HOME="$RUNTIME_HOME" PATH="$RUNTIME_PATH" a-stock-install --help
  HOME="$RUNTIME_HOME" PATH="$RUNTIME_PATH" \
    A_STOCK_STATE_DIR="$(mktemp -d)" a-stock-cache checklist 000001 A
)
HOME="$RUNTIME_HOME" PATH="/usr/bin:/bin" python3 scripts/install.py \
  --client all --mode symlink --source "$SUITE" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE"; test $? -ne 0
```

最后一条必须只因稳定 CLI 目录不在 `PATH` 而失败，并给出修复提示。

再构建一次可校验 wheel，在另一个临时 HOME 以 `--a-stock-lib-wheel` 重跑同一安装、import 和随机 cwd CLI smoke；`tests/test_installation.py` 必须同时覆盖 source 与 wheel 两条输入路径，且拒绝二者同时缺失或同时提供。

## Task M4.3：三端发现机制只读探测

先在隔离 target root 验证文件结构；不得替换真实用户目录。

真实三端业务 smoke 留到 M6。M4 必须为当前已安装的客户端版本实测并记录一条不修改 active Skill 的 shadow discovery 方式：Claude/Codex 优先使用临时项目 cwd，Hermes 使用 invocation 级 `HERMES_HOME` 或等价隔离 profile。记录实际版本、命令、发现路径和退出码到 `docs/migration/client-shadow-invocation.md`，不得记录凭证。若任一客户端只能通过替换用户级 active Skill 才能发现测试 Skill，则 M4 失败并暂停，不把该替换提前到 M6。

最低只读探测：

```bash
hermes skills list
codex --version
claude --version
```

**阶段验证：**

```bash
cd "$SUITE"
uv run pytest tests/test_installation.py tests/test_portability.py -q
uv run pytest -q
codex review --uncommitted
```

```bash
git add scripts/install.py src/a_stock_agent_runtime/install.py tests

git commit -m 'feat: add reversible three-client skill installer'
```

**M4 回滚：** 使用测试 installer 生成的 rollback manifest并删除临时 HOME。本阶段不触碰真实客户端目录；M6 的真实 shadow 入口使用同一 rollback 合同。

---

# M5：状态外置、迁移工具和 cron 候选

## Task M5.1：状态迁移工具（仅隔离 fixture）

**创建：**

- `scripts/migrate_state.py`
- `tests/test_state_migration.py`
- `tests/fixtures/sqlite/source.db`（测试生成，不提交二进制 DB；测试运行时创建）

参数合同：

```text
--source-db <path>
--target-db <path>
--report <json-path>
--dry-run
--expected-table <name>  # repeatable
```

实现使用 `sqlite3.Connection.backup`；报告包含 source/target hash、journal mode、user_version、schema/关键表集合、holdings/交易事件/analysis_results 行数、关键持仓字段抽样和 integrity。不得读取 Telegram 配置。

**验证：**

```bash
cd "$SUITE"
uv run pytest tests/test_state_migration.py -q
TMP=$(mktemp -d)
uv run python - "$TMP/source.db" <<'PY'
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as conn:
    conn.execute("CREATE TABLE holdings(code TEXT PRIMARY KEY, shares INTEGER NOT NULL)")
    conn.execute("INSERT INTO holdings VALUES ('000001', 100)")
PY
uv run python scripts/migrate_state.py \
  --source-db "$TMP/source.db" --target-db "$TMP/target.db" \
  --report "$TMP/report.json" --dry-run
find "$TMP" -maxdepth 1 -type f -print
```

Dry-run 后只允许已有的 `source.db`；不得生成目标 DB 或 report。

## Task M5.2：Cron 候选脚本

**修改：**

- `scripts/check-holdings-cron.sh`
- `tests/test_check_holdings_cron.sh`

要求：

- 调用 `a-stock-cache check-holdings`，不调用 Skill 文件；
- 只加载 `A_STOCK_CONFIG_FILE`；
- `A_STOCK_NOTIFY_MODE=disabled` 时绝不执行 curl；
- Telegram token/chat 缺失时生产模式非零失败并记录；
- log/lock 来自外置目录；
- 测试使用假的 `curl`/`a-stock-cache` 和临时 PATH；
- 不 source tracker `.env`。

**验证：**

```bash
cd "$SUITE"
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
uv run pytest tests/test_side_effect_boundaries.py -q
rg -n 'a-stock-tracker/\.env|\.claude/skills|cache\.py' scripts/check-holdings-cron.sh
```

最后一条必须无输出。

## Task M5.3：状态和副作用全量门禁

```bash
cd "$SUITE"
uv run pytest tests/test_state_migration.py tests/test_side_effect_boundaries.py -q
uv run pytest -q
uv run ruff check src tests scripts
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck scripts/check-holdings-cron.sh
else
  bash -n scripts/check-holdings-cron.sh
  bash tests/test_check_holdings_cron.sh
fi
codex review --uncommitted
```

```bash
git add scripts tests src
git commit -m 'feat: externalize state and add safe migration tooling'
```

**M5 回滚：** `git revert <M5-commit>`。此阶段只操作 fixture，不涉及生产 DB/cron。

---

# M6：三端 Shadow 验证

## Task M6.1：准备隔离 evidence packet

**创建：**

- `tests/fixtures/research/framework-{A,B,C,D,E,F}.json`
- `tests/fixtures/research/stale-quote.json`
- `tests/fixtures/research/missing-financial-field.json`
- `tests/fixtures/monitor/holdings-l3.json`
- `tests/fixtures/qa/{compliant,non_compliant,unknown_rubric}.md`
- `tests/golden/*.json`
- `docs/reviews/client-shadow-<run-id>/`

每端统一注入：

```bash
export A_STOCK_STATE_DIR=$(mktemp -d)
export CACHE_DB_PATH="$A_STOCK_STATE_DIR/cache.db"
export A_STOCK_LOG_DIR="$A_STOCK_STATE_DIR/logs"
export A_STOCK_LOCK_DIR="$A_STOCK_STATE_DIR/locks"
export A_STOCK_ARTIFACT_DIR="$A_STOCK_STATE_DIR/artifacts"
export A_STOCK_NOTIFY_MODE=disabled
unset TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID
```

Fixture smoke 不联网、不使用生产凭证；模型只读取 evidence packet。

## Task M6.2：盘点 active 入口并安装隔离 shadow

这是 M0-M6 持续 Goal 已覆盖的可回滚 shadow 安装，不再请求 M6 或逐客户端批准。M6 不复制可能正在变化的生产 DB，也不替换用户级 active Skill；先以 `lstat`、`readlink`、文件清单和 hash 做只读盘点，再安装到新的临时 target。若临时 target 已存在内容，installer 仍须按 Spec 先备份并输出仓库外 rollback manifest。

正式 shadow 前检查现有入口是否包含 DB/WAL/SHM，或是否被当前 crontab/脚本引用；结果写入 evidence，且无论是否命中都只使用 M4 已验证的 project/profile 隔离入口。真实用户级入口及其完整备份留到 writer 已暂停的 M7。

**只读盘点与隔离安装：**

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)
EVIDENCE="$SUITE/docs/reviews/client-shadow-$RUN_ID"
mkdir -p "$EVIDENCE"
for name in a-stock-research a-stock-monitor a-stock-qa; do
  for client in claude codex hermes; do
    case "$client" in
      claude) p="$HOME/.claude/skills/$name" ;;
      codex)  p="$HOME/.agents/skills/$name" ;;
      hermes) p="$HOME/.hermes/skills/research/$name" ;;
    esac
    if [ -e "$p" ] || [ -L "$p" ]; then
      printf '%s\n' "$p" >> "$EVIDENCE/active-entry-paths.txt"
      stat -c '%N %F %s %y' "$p" >> "$EVIDENCE/active-entry-stat.txt"
      readlink "$p" >> "$EVIDENCE/active-entry-links.txt" 2>/dev/null || true
      find -L "$p" -maxdepth 2 -type f -printf '%P\n' | sort \
        >> "$EVIDENCE/active-entry-files.txt"
      find -L "$p" -maxdepth 2 -type f \
        \( -name '*.md' -o -name '*.py' -o -name '*.sh' \) \
        -exec sha256sum {} + >> "$EVIDENCE/active-entry-source.sha256"
    fi
  done
done
SHADOW_ROOT=$(mktemp -d)
python3 "$SUITE/scripts/install.py" --client all --mode symlink \
  --source "$SUITE" --target-root "$SHADOW_ROOT" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE" --dry-run
python3 "$SUITE/scripts/install.py" --client all --mode symlink \
  --source "$SUITE" --target-root "$SHADOW_ROOT" \
  --a-stock-lib-source "$A_STOCK_LIB_SOURCE"
```

每个客户端进程必须按 M4 的 `client-shadow-invocation.md` 使用 project/profile 入口指向 `$SHADOW_ROOT`，并在 evidence 中记录实际 discovery path。M6 不替换任何用户级入口；真实切换合并到 M7。

## Task M6.3：Claude Code shadow

```bash
NORMAL_FIXTURE="$SUITE/tests/fixtures/research/framework-A.json"
STALE_FIXTURE="$SUITE/tests/fixtures/research/stale-quote.json"
cd "$SHADOW_ROOT"
claude -p --permission-mode plan --no-session-persistence --add-dir "$SUITE" \
  "/a-stock-research 使用本地 fixture $NORMAL_FIXTURE 做只读框架路由；禁止网络、数据库写入和通知，只返回框架、硬评分结构、数据缺口和 fail-closed 状态。"
claude -p --permission-mode plan --no-session-persistence --add-dir "$SUITE" \
  "/a-stock-research 使用本地 fixture $STALE_FIXTURE；禁止网络、数据库写入和通知，证明过期且无法刷新时 fail-closed。"
claude -p --permission-mode plan --no-session-persistence --add-dir "$SUITE" \
  "/a-stock-monitor 使用本地 fixture $SUITE/tests/fixtures/monitor/holdings-l3.json 做只读检查；禁止网络、写入和通知。"
claude -p --permission-mode plan --no-session-persistence --add-dir "$SUITE" \
  "/a-stock-qa 检查 $SUITE/tests/fixtures/qa/compliant.md；只读取 research rubric，不执行任何 runtime CLI。"
```

输出和退出码保存到 client-shadow evidence 目录。

## Task M6.4：Codex shadow

```bash
codex exec -s read-only -C "$SHADOW_ROOT" --add-dir "$SUITE" --ephemeral --color never \
  "Explicitly use \$a-stock-research with local fixture $NORMAL_FIXTURE. No network, DB writes, or notifications. Return only framework route, deterministic score structure, data gaps, and fail-closed status."
codex exec -s read-only -C "$SHADOW_ROOT" --add-dir "$SUITE" --ephemeral --color never \
  "Explicitly use \$a-stock-research with local fixture $STALE_FIXTURE. No network, DB writes, or notifications; prove it fails closed."
codex exec -s read-only -C "$SHADOW_ROOT" --add-dir "$SUITE" --ephemeral --color never \
  "Explicitly use \$a-stock-monitor with $SUITE/tests/fixtures/monitor/holdings-l3.json. Read only; no network, writes, or notifications."
codex exec -s read-only -C "$SHADOW_ROOT" --add-dir "$SUITE" --ephemeral --color never \
  "Explicitly use \$a-stock-qa on $SUITE/tests/fixtures/qa/compliant.md. Read only the research rubric and do not execute runtime commands."
```

## Task M6.5：Hermes shadow

```bash
cd "$SHADOW_ROOT"
HERMES_HOME="$SHADOW_ROOT/.hermes" hermes chat -q -Q -t file,skills \
  -s a-stock-research --max-turns 4 \
  "使用本地 fixture $NORMAL_FIXTURE 做只读框架路由；禁止网络、数据库写入和通知，只返回框架、硬评分结构、数据缺口和 fail-closed 状态。"
HERMES_HOME="$SHADOW_ROOT/.hermes" hermes chat -q -Q -t file,skills \
  -s a-stock-research --max-turns 4 \
  "使用本地 fixture $STALE_FIXTURE；禁止网络、数据库写入和通知，证明过期且无法刷新时 fail-closed。"
HERMES_HOME="$SHADOW_ROOT/.hermes" hermes chat -q -Q -t file,skills \
  -s a-stock-monitor --max-turns 4 \
  "使用本地 fixture $SUITE/tests/fixtures/monitor/holdings-l3.json 做只读检查；禁止网络、写入和通知。"
HERMES_HOME="$SHADOW_ROOT/.hermes" hermes chat -q -Q -t file,skills \
  -s a-stock-qa --max-turns 4 \
  "检查 $SUITE/tests/fixtures/qa/compliant.md；只读取 research rubric，不执行任何 runtime CLI。"
```

不得使用会自动绕过危险命令审批的 `-z/--oneshot`。若新 Skill 在当前 gateway/session 中因缓存不可见，使用上述新的隔离 chat 进程验证；gateway 重启不属于 M6 默认授权。

## Task M6.6：比较不变量

**创建：** `scripts/compare_shadow_results.py` 和对应测试。

比较：

- 三个 Skill 的 discovery 和显式 invocation；
- 框架路由；
- 硬评分字段/上限；
- 红线；
- 数据缺口；
- fail-closed 状态；
- 随机 cwd 下三个公开 CLI 的 PATH 发现；
- QA 检查未调用 runtime、行情网络或市场数据依赖；
- DB/log/Telegram 无副作用。

不比较完整自然语言。

```bash
uv run python scripts/compare_shadow_results.py docs/reviews/client-shadow-<run-id>
find "$A_STOCK_STATE_DIR" -maxdepth 2 -type f -printf '%P %s\n' | sort
find "$SHADOW_ROOT" -type f \( -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' \
  -o -name '.env' -o -path '*/logs/*' -o -path '*/locks/*' \) -print
codex review --uncommitted
```

最后一条 `find` 必须无输出；三端安装 manifest 的 release commit 和 source hash 必须一致。

**M6 回滚：** 若 installer 对非空临时 target 生成过 rollback manifest，则按 manifest 恢复；随后删除隔离 target/state。不触碰用户级 Skill、生产 DB 或 cron。

---

# M7：生产 DB、cron 和 Hermes 切换

> 高风险阶段。开始前必须由用户一次明确批准 M7；批准实施计划或 M0-M6 不自动批准 M7。该次 cutover 审批合并备份、暂停 writer、DB/配置/active Skill/cron/Telegram 切换、Hermes smoke 和失败回滚，不拆成多次项目审批。

## Task M7.1：维护窗口与备份

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)
EVIDENCE="$SUITE/docs/migration/production-cutover/$RUN_ID"
mkdir -p "$EVIDENCE"
crontab -l > "$EVIDENCE/crontab.before"
sha256sum "$SRC_RESEARCH/cache.db" > "$EVIDENCE/source-db.sha256.before"
stat -c '%n %s %y' "$SRC_RESEARCH/cache.db" > "$EVIDENCE/source-db.stat.before"
```

列出并停止所有访问旧 DB 的 cron/进程。不得使用模糊 kill；记录确切 PID/任务。停止后用 `fuser`/`lsof` 证明无 writer。

## Task M7.2：生产 SQLite 一致快照

```bash
export A_STOCK_STATE_DIR="$HOME/.local/share/a-stock-agent"
export CACHE_DB_PATH="$A_STOCK_STATE_DIR/cache.db"
install -d -m 0700 "$A_STOCK_STATE_DIR" "$A_STOCK_STATE_DIR/logs" \
  "$A_STOCK_STATE_DIR/locks" "$A_STOCK_STATE_DIR/artifacts"

uv run python "$SUITE/scripts/migrate_state.py" \
  --source-db "$SRC_RESEARCH/cache.db" \
  --target-db "$CACHE_DB_PATH" \
  --report "$EVIDENCE/db-migration.json" \
  --expected-table holdings \
  --expected-table analysis_results
```

目标验证必须在 migration 工具内以只读 URI 完成并记录；不手工裸 `cp` 主 DB。

**停止：** integrity 非 ok、schema/user_version/关键表计数或持仓抽样不一致、发现 writer。

## Task M7.3：生产配置、active Skill 和 cron 候选

**创建（仓库外）：**

- `~/.config/a-stock-agent/runtime.env`，权限 0600；
- `~/.local/share/a-stock-agent/*`，权限 0700。

配置必须显式：

```text
A_STOCK_STATE_DIR=/home/lin/.local/share/a-stock-agent
CACHE_DB_PATH=/home/lin/.local/share/a-stock-agent/cache.db
A_STOCK_LOG_DIR=/home/lin/.local/share/a-stock-agent/logs
A_STOCK_LOCK_DIR=/home/lin/.local/share/a-stock-agent/locks
A_STOCK_ARTIFACT_DIR=/home/lin/.local/share/a-stock-agent/artifacts
A_STOCK_NOTIFY_MODE=telegram
```

Telegram 凭证通过现有受保护 secret/config 管理迁移，不在 evidence 中打印。

writer 暂停且 DB 快照验证通过后，由 installer 为现有用户级入口新建仓库外备份和 rollback manifest，再把三个客户端入口切到同一 canonical release；先 dry-run，再带 `--force` 正式执行。此时 cron 仍保持暂停：

```bash
python3 "$SUITE/scripts/install.py" --client all --mode symlink \
  --source "$SUITE" --a-stock-lib-source "$A_STOCK_LIB_SOURCE" --force --dry-run
python3 "$SUITE/scripts/install.py" --client all --mode symlink \
  --source "$SUITE" --a-stock-lib-source "$A_STOCK_LIB_SOURCE" --force
```

先生成候选 crontab：

```bash
cp "$EVIDENCE/crontab.before" "$EVIDENCE/crontab.candidate"
```

只替换持仓检查任务为新 canonical cron 脚本/CLI；tracker 自己的其他任务不变。检查候选 diff 后才：

```bash
crontab "$EVIDENCE/crontab.candidate"
crontab -l > "$EVIDENCE/crontab.after"
diff -u "$EVIDENCE/crontab.before" "$EVIDENCE/crontab.after" > "$EVIDENCE/crontab.diff" || true
```

## Task M7.4：Hermes production candidate smoke

先禁通知：

```bash
A_STOCK_NOTIFY_MODE=disabled \
A_STOCK_CONFIG_FILE="$HOME/.config/a-stock-agent/runtime.env" \
a-stock-cache holdings

A_STOCK_NOTIFY_MODE=disabled \
A_STOCK_CONFIG_FILE="$HOME/.config/a-stock-agent/runtime.env" \
a-stock-cache portfolio-risk
```

然后 Hermes 做一次真实 research 候选；网络读取和分析缓存写入必须由本次明确请求授权，持仓写入禁止。

检查：

- Hermes 识别 canonical Skill；
- 运行命令来自新 venv/PATH；
- 无 `.claude/skills`/Claude CLI；
- 读取目标 DB；
- 无持仓/账本变化；
- 通知关闭时无 Telegram 请求。

## Task M7.5：恢复 cron

只在 M7.2-M7.4 全绿后启用候选 cron。首次运行前先：

```bash
A_STOCK_NOTIFY_MODE=disabled \
A_STOCK_CONFIG_FILE="$HOME/.config/a-stock-agent/runtime.env" \
bash "$SUITE/scripts/check-holdings-cron.sh"
```

生产 Telegram 启用和一次受控通知验证必须包含在 M7 cutover 审批列出的动作中，不能通过真实止损伪造告警，也不在阶段内再次请求项目批准。

## Task M7.6：切换证据和聚焦复审

```bash
git -C "$SUITE" status --short
git -C "$SRC_RESEARCH" status --short
git -C "$A_STOCK_LIB_SOURCE" status --short
codex exec -s read-only -C "$SUITE" --ephemeral \
  'Review only the production cutover evidence for DB integrity, cron single-active behavior, state path, notification boundary, rollback, and absence of legacy Claude runtime paths. Do not edit files.'
```

Hermes 父级逐项核验后才宣布切换完成。

### M7 回滚

无新生产写入时：

1. 停新 cron；
2. `crontab "$EVIDENCE/crontab.before"`；
3. 恢复旧 Skill 入口备份；
4. 恢复旧 `CACHE_DB_PATH`；
5. 验证旧 DB/cron；
6. 禁用新 Telegram 通知。

若新 DB 已有生产写入：

- 不得直接切回旧 DB；
- 立即停止所有 writer；
- 导出新旧交易事件/持仓差异；
- 人工 reconciliation 后再决定正向或反向迁移。

---

# M8：稳定、回滚演练和 Claude 停用

## Task M8.1：稳定期验收

至少覆盖：

- Hermes research 正常和 fail-closed；
- Monitor holdings/L3/portfolio-risk；
- QA compliant/non-compliant/SKIP；
- cron 首次预期执行；
- Telegram 只在真实条件或受控测试下发送；
- Claude/Codex 仍可在隔离状态发现 Skill；
- source/installation hashes 无漂移。

## Task M8.2：回滚演练

在隔离 target/state 中执行 installer rollback 和 DB fixture rollback，不操作生产 DB。验证回滚 manifest 可用后记录结果。

## Task M8.3：停用 Claude 入口

默认必须单独获得用户确认；若 M7 审批已明确包含“约定稳定期通过后停用 Claude”及其判定条件，则沿用该授权，不重复询问。只停用：

- Claude 作为 A 股生产交互入口；
- Claude 相关 A 股自动调用。

不删除：

- 旧 Git 仓库；
- 旧 DB 快照；
- Claude Code 的只读兼容 Skill（除非用户另行要求）；
- 迁移 evidence。

停用后验证进程、cron 和日志中不再调用 Claude CLI。

---

# 3. 最终验证矩阵

| Gate | 命令/证据 | 预期 |
|---|---|---|
| Spec | Goal 启动时记录的当前 Spec hash | 与确认基线一致 |
| Runtime imports | `uv run pytest tests/test_import_graph.py` | pass |
| CLI | `uv run pytest tests/test_cli_contract.py tests/test_command_classification.py` | 3 个公开 main；命令分类完整 |
| Research | `uv run pytest tests/research -q` | all pass |
| Monitor | `uv run pytest tests/monitor -q` | 12+ pass |
| QA | `uv run pytest tests/qa -q` | compliant/non-compliant/SKIP pass |
| a-stock-lib | `.venv/bin/python -m pytest -p no:cacheprovider tests -q` | all pass |
| Skills | `uv run python scripts/validate.py` | 3 valid |
| Installer | `uv run pytest tests/test_installation.py` | pass |
| Release traceability | 三端 installer manifest | 同一 release commit/source hash，无未声明分叉 |
| Runtime PATH | 临时 HOME/PATH + 随机 cwd smoke | 3 个公开 CLI 可发现；checklist 经 cache 子命令 |
| Paths | `uv run pytest tests/test_paths.py` | pass |
| State migration | `uv run pytest tests/test_state_migration.py` | pass |
| Side effects | `uv run pytest tests/test_side_effect_boundaries.py` | pass |
| Cron | `bash -n` + shell regression | pass, no real Telegram |
| Three clients | client-shadow evidence | invariant match |
| QA standalone | `python3 -I tests/qa/standalone_smoke.py` + 三端 shadow | 无 runtime/行情依赖 |
| W1 safety | classification + side-effect tests | 缺 `--confirm-write` 返回 3 且 DB 不变 |
| Production DB | migration JSON | integrity ok + counts/sample match |
| Cron cutover | before/after/diff | single active |
| Hermes | production candidate evidence | canonical Skill/runtime, no Claude path |
| Review | per-phase Codex output | no unresolved blocker |
| Evidence | 每阶段 review 目录 | prompt/stdout/stderr/exit code/hash/drift 完整且无秘密 |
| Git | status/diff | expected changes only |

# 4. Plan readiness self-audit

- Exact project/source/active paths：已列出。
- Exact target files：按每个 Task 列出。
- Commands：已给出；生产命令位于单独 M7 gate。
- Rollback：M1-M8 分层定义。
- Secret boundary：不复制、不打印、不写入 repo/evidence。
- DB boundary：fixture-first；生产 Online Backup 只包含在 M7 一次 cutover 批准中。
- Cron/Telegram boundary：candidate-first，notify disabled 默认。
- Golden-master：比较结构与安全不变量，不比较全文。
- Independent review：每阶段 Codex review，父级复核；均属于持续 Goal 内质量检查。
- No promotion：M7 已由用户一次性 cutover 请求授权并完成；本计划不授权 M8 Claude 停用。
- No placeholders：`<run-id>` 等仅是实施时由 `date` 生成的运行标识，不是未定义设计决策。

# 5. 下一授权点

用户一次明确要求“按 Spec 开始实施”即批准一个持续 Goal 执行 **M0-M6**：冻结证据、canonical 仓库、runtime、三个 Skill、installer、fixture 状态工具和隔离的三端 shadow；阶段验收后自动进入下一阶段，不重复请求项目批准。

M7 必须一次单独明确授权。M8 默认在稳定期验收后单独确认；若 M7 已明确包含带判定条件的 Claude 停用授权，则不重复请求。
