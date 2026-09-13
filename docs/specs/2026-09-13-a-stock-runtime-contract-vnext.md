# A-stock Runtime Contract vNext
## 基于最新项目状态的调整版 Codex 实施 Spec

> Date: 2026-09-13
> Status: **IMPLEMENTED / COMPLETE**
>
> Scope:
> - `on195594/a-stock-lib`
> - `on195594/a-stock-agent-skills`
>
> Development policy:
> - 仅在 `master` 开发
> - 不创建 feature branch
> - 不使用 PR
> - 小步 commit + push `master`
> - 禁止 force push
>
> 本 Spec **取代**此前 `A-stock Contract & Audit Architecture vNext` 中已经完成或已过时的工作项。

---

# 0. 当前事实基线

## 0.1 a-stock-lib

```text
implementation head:
f7fd9df1bf3cf88148019cd0d1ed4aa5c46d5367

package version:
0.8.0

published release:
v0.8.0

release tag commit:
47d315e34bcc8d2b992cdf338437cbea3d7e9619

release wheel:
a_stock_lib-0.8.0-py3-none-any.whl

SHA256:
a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310
```

当前 `master` 比 `v0.8.0` tag 更新；release 之后增加了文档、CI、测试、tooling 和 development lock，但没有 `a_stock_lib/**` 或 `pyproject.toml` 的 wheel-relevant drift。

`uv.lock` 已更新到 `0.8.0` 并纳入版本控制；published-version guard 明确保护已发布 wheel identity，同时检查已提交、暂存、未暂存和未跟踪的 artifact-relevant 变化。

因此：**v0.8.0 发布身份当前是干净且受自动门禁保护的。**

## 0.2 a-stock-agent-skills

```text
implementation head:
266cd5e384fe859fe5e7a19d619d716555499947

package version:
0.1.13
```

当前依赖：

```text
a-stock-lib v0.8.0 Release wheel
SHA256:
a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310
```

与正式 GitHub Release asset 一致。

## 0.3 Real Tool E2E 已完成

当前已存在：

```text
scripts/capture_agent_tool_e2e.mjs
tests/test_agent_tool_e2e.py
tests/fixtures/agent_tool_e2e_live.json
```

Live capture 使用：

```text
provider = openai-codex
model = gpt-5.6-sol
```

并由真实 Agent 直接调用隔离的 in-process fake tools。

当前实际调用序列：

```text
Research:
1. a_stock_cache holdings
2. a_stock_fetch
3. a_stock_cache check

Monitor clean:
4. a_stock_cache monitor-snapshot

Unauthorized W1:
5. a_stock_cache monitor-snapshot
```

fake W1 tool 已暴露但没有被调用。

因此：**真实 Agent 实际调用 fake tool 不再是待办。**

## 0.4 最新 CI

```text
a-stock-lib/f7fd9df CI = success
a-stock-agent-skills/3ca88c5 CI = success
```

---

# 1. 重新评估结论

以下事项已经完成，不再重复执行：

```text
[x] a-stock-lib 0.8.0 package line
[x] GitHub Release v0.8.0
[x] consumer pin v0.8.0 + SHA256
[x] agent package version从 0.1.11 前进到 0.1.13
[x] fake-tool Agent actual execution
[x] offline verifier
[x] Unauthorized W1 actual non-execution
```

本轮工作已经全部落地：

```text
[x] monitor-v1 contract 抽取与强化
[x] framework routing catalog 显式化
[x] published-version drift 自动门禁
[x] live E2E provenance 加固
[x] runtime contract 架构文档
```

---

# 2. 本轮目标

## Goal A — Formalize monitor-v1

当前 Monitor 已经拥有 `schema_version = 1` 和内联 `validate_monitor_snapshot()`，但 contract owner 仍埋在 `commands_monitor.py`。

目标：

```text
current monitor-v1 wire shape
        ↓
monitor_contract.py
        ↓
versioned validation / serialization
```

不改变现有业务语义。

## Goal B — Explicit Framework Routing Catalog

消除：

```python
from a_stock_agent_runtime import checklist  # noqa: F401
```

这种为了 registry side effect 而发生的隐藏 import。

## Goal C — Prevent Future Published-Version Drift

当前 v0.8.0 没有源码漂移，但仓库缺少自动门禁，防止未来出现：

```text
released v0.8.0
+
package source changed
+
version still 0.8.0
```

## Goal D — Harden E2E Provenance

当前 live E2E 已证明真实 tool execution。

下一步只加固 artifact：

```text
repository head
capture script hash
individual Skill hashes
exposed tool list
structured isolation metadata
```

---

# 3. 非目标

```text
× 再发布 a-stock-lib 新版本
× 将 agent 强制跳到 0.2.0
× 重做 fake-tool E2E
× 增加更多 Agent scenario
× 大规模拆 commands_monitor.py
× 大规模拆 commands_holdings.py
× 重写 fetcher.py
× 引入 Pydantic
× 引入 ORM
× 建 schema registry 服务
× 新建 a-stock-policy 仓库
× 将 L3 / Tier / holdings 移入 a-stock-lib
× 修改投资策略阈值
× 修改 W1 授权模型
× 修改生产 DB schema
```

---

# 4. 执行规则

## 4.1 Branch guard

```bash
git checkout master
git pull --ff-only origin master
test "$(git branch --show-current)" = "master"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git rev-parse HEAD
```

失败立即停止。

实施前发现 `a-stock-lib/uv.lock` 是未跟踪且仍指向 `0.7.0` 的旧 development lock。为避免本地与 CI 使用不同解析结果，已将其更新到 `0.8.0` 并提交；不得仅用 `.gitignore` 隐藏仍会被 `uv` 消费的本地 lock。

## 4.2 Commit discipline

```text
1. 记录 baseline SHA
2. focused baseline tests
3. 修改最小文件集合
4. focused tests
5. full gate
6. git diff --check
7. review diff
8. git add explicit files
9. git commit
10. git push origin master
11. read-back remote SHA
```

禁止：

```text
force push
reset published history
跨阶段大提交
```

---

# 5. Phase 1 — Published-Version Drift Guard

**仓库：** `a-stock-lib`

本 Phase 不修改：

```text
a_stock_lib/**
pyproject version
```

因此 package version 保持 `0.8.0`。

## 5.1 新增 guard

新增：

```text
scripts/check_published_version_identity.py
```

## 5.2 Guard 语义

读取 `pyproject.toml project.version`，构造：

```text
tag = v{version}
```

### Case A — 当前版本没有 tag

```text
PASS
```

表示尚未发布 development version。

### Case B — HEAD == release tag commit

```text
PASS
```

### Case C — release tag 已存在

检查以下路径集合的并集：

```text
v${VERSION}..HEAD 的已提交变化
HEAD 相对 index/worktree 的 staged 与 unstaged 变化
未被 ignore 的 untracked 文件
```

这样 full gate 在 commit 前即可阻止复用已发布版本，不能只依赖 push 后 CI。

只判断 published-wheel-relevant paths：

```text
a_stock_lib/**
pyproject.toml
MANIFEST.in
setup.py
setup.cfg
```

只有 docs / CI / tooling / development lock 改动时 PASS。这里的 identity 明确指 GitHub Release 中发布的 wheel；若未来发布 sdist，必须单独扩展 sdist-relevant path 集合。

wheel-relevant path 有变化时 FAIL：

```text
published package version reused after artifact-relevant source changed
```

## 5.3 Annotated tag

使用：

```bash
git rev-list -n 1 v${VERSION}
```

不要假设 tag ref 直接指向 commit。

## 5.4 CI history

`.github/workflows/ci.yml` 的 checkout 改为：

```yaml
with:
  persist-credentials: false
  fetch-depth: 0
```

## 5.5 Guard tests

新增：

```text
tests/test_published_version_identity.py
```

核心判断建议：

```python
check_repository(repo: Path) -> list[str]
```

测试：

```text
no matching tag → pass
HEAD == tag → pass
docs-only after tag → pass
committed a_stock_lib source changed → fail
pyproject changed under released version → fail
staged / unstaged / untracked a_stock_lib source changed → fail
annotated tag → correct
```

使用临时 git repo，禁止 GitHub API。

## 5.6 CI gate

增加：

```bash
python scripts/check_published_version_identity.py
```

## Done

```text
[x] 当前 0.8.0 + non-wheel master changes 能通过
[x] committed / staged / unstaged / untracked package source drift 会失败
[x] guard 完全离线
[x] annotated tag 正确处理
```

---

# 6. Phase 2 — Start Agent 0.1.13 Development Line

**仓库：** `a-stock-agent-skills`

后续会修改 runtime package source：

```text
monitor contract
framework routing
```

因此将：

```text
0.1.12 → 0.1.13
```

## 6.1 不升级到 0.2.0

本轮目标是 wire-compatible / behavior-compatible，因此 `0.1.13` 足够。

除非出现 deliberate breaking public contract，否则不得自行升级到 0.2.0。

## 6.2 lib pin 保持

继续：

```text
a-stock-lib 0.8.0
sha256:
a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310
```

本轮不发布新 lib。

## 6.3 Version owner

`pyproject.toml` 是 package version owner。

如果没有 runtime `__version__`，不要新增第二个 version source。

更新 current-state README、CHANGELOG、tests、uv.lock；历史 migration evidence 不改写。

---

# 7. Phase 3 — monitor-v1 Contract Extraction & Hardening

**仓库：** `a-stock-agent-skills`

## 7.1 当前事实

当前 `commands_monitor.py` 已经构造：

```text
schema_version
as_of
runtime_version
data_status
valuation_status
review_status
action_status
account
quote_coverage
industry_context
holdings
escalations
data_gaps
stop_reason
requires_user_confirmation
manifest
```

并内联 `validate_monitor_snapshot()`。

因此本 Phase 不设计 monitor-v2，也不重命名字段。

## 7.2 新 contract owner

新增：

```text
src/a_stock_agent_runtime/monitor_contract.py
```

API：

```python
class MonitorContractError(ValueError):
    ...

def validate_monitor_snapshot(payload: object) -> dict[str, Any]:
    ...

def loads_monitor_snapshot(text: str) -> dict[str, Any]:
    ...

def dumps_monitor_snapshot(payload: object) -> str:
    ...
```

风格与 `decision_contract.py` 对齐。

## 7.3 Wire shape freeze

`schema_version = 1` 不变。

禁止：

```text
as_of -> generated_at
account -> portfolio
quote_coverage -> coverage
```

字段重命名只能进入未来 `monitor-v2`。

## 7.4 Unavailable snapshot normalization

当前 unavailable path 缺少 `industry_context`。

允许唯一一个 additive normalization：

```json
"industry_context": {
  "status": "not_applicable",
  "error_code": null,
  "freshness_days": null,
  "source": null,
  "fetched_at": null
}
```

## 7.5 Protocol vocabulary owner

移入 `monitor_contract.py`：

```text
DATA_STATUSES
VALUATION_STATUSES
REVIEW_STATUSES
ACTION_STATUSES
INDUSTRY_CONTEXT_STATUSES
ESCALATION_REASON_CODES
```

`commands_monitor.py` 不得维护第二份合法值集合。

排序优先级 `_ESCALATION_REASON_ORDER` 可留在 workflow 层，但测试：

```text
set(_ESCALATION_REASON_ORDER) == ESCALATION_REASON_CODES
```

## 7.6 Required top-level fields

```text
schema_version
as_of
runtime_version
data_status
valuation_status
review_status
action_status
account
quote_coverage
industry_context
holdings
escalations
data_gaps
stop_reason
requires_user_confirmation
manifest
```

Unknown additive fields ACCEPT。

容器类型必须先验证：`account`、`quote_coverage`、`industry_context`、`manifest` 为 object；`holdings`、`escalations`、`data_gaps` 为 array。结构错误统一抛出 `MonitorContractError`，不得泄漏 `KeyError` / `TypeError`。

## 7.7 Basic validation

### schema_version

```text
type is int
== 1
```

`True` 不得当成 1。所有 integer 字段都使用严格 `type(value) is int`，所有 boolean 字段都使用严格 `type(value) is bool`，不得接受 Python 的 bool/int 等价。

### as_of

```text
non-empty ISO-8601
timezone-aware
```

### runtime_version

```text
non-empty string
```

contract 不负责读取 metadata。

## 7.8 Status vocabulary

### data_status

```text
complete
partial
stale
unavailable
conflicted
```

### valuation_status

```text
exact
priced_positions_lower_bound
unavailable
```

### review_status

```text
cleared
review_required
blocked
```

### action_status

```text
no_action
review_candidate
trade_candidate
```

## 7.9 quote_coverage

```text
priced / active:
type int
>= 0

priced <= active

complete:
strict bool
```

若 `complete == true`，必须 `priced == active`。

但 `priced == active == 0` 不强制 `complete=true`，保留 unavailable 语义。

## 7.10 industry_context

required：

```text
status
error_code
freshness_days
source
fetched_at
```

status：

```text
complete
stale
invalid
unavailable
not_applicable
```

规则：

```text
complete → error_code is null
freshness_days → null or int >= 0
fetched_at → null or valid ISO-8601
```

## 7.11 holdings[]

第一版只固化：

```text
id
code
name
framework
framework_confident
quote
```

要求：

```text
code = six-digit string
quote = object
```

Tier / L3 / risk_gates / alerts / p3 保留 additive。

## 7.12 escalations[]

required：

```text
code
reason_code
candidate
detail
```

candidate：

```text
review
trade
```

reason_code 必须属于 `ESCALATION_REASON_CODES`。

detail non-empty。

## 7.13 data_gaps[]

required：

```text
code
field
minimum_action
```

`field` / `minimum_action` non-empty。

## 7.14 Cross-field invariants

### I1

```text
data_status != complete
→ action_status != no_action
```

如现有测试证明合法例外，则 STOP，不覆盖现有业务。

### I2

```text
action_status == trade_candidate
→ 至少一个 escalation.candidate == trade
```

### I3

```text
industry_context.status in {stale, invalid, unavailable}
and holdings 非空
→ data_gaps 至少一个 field == industry_context
```

### I4

```text
requires_user_confirmation
==
(action_status == trade_candidate)
```

### I5

递归拒绝 NaN / Infinity / -Infinity。

### I6

```text
type(manifest.writes) is bool
manifest.writes == false
```

### I7

```text
manifest.stop_reason == top-level stop_reason
```

### I8 clean_fast_gate

若：

```text
stop_reason == clean_fast_gate
```

则：

```text
data_status == complete
valuation_status == exact
review_status == cleared
action_status == no_action
escalations == []
data_gaps == []
quote_coverage.complete == true
```

## 7.15 Serialization

`dumps_monitor_snapshot()`：

```text
validate first
ensure_ascii=False
sort_keys=True
compact separators
allow_nan=False
```

`loads_monitor_snapshot()`：

```text
reject non-finite JSON constants
validate after parse
```

## 7.16 commands_monitor integration

正常和 unavailable path 都必须走 `monitor_contract`。

Monitor snapshot CLI 不再直接 `json.dumps(payload)`，而是：

```python
monitor_contract.dumps_monitor_snapshot(payload)
```

## 7.17 Compatibility regression

先锁住代表性输出：

```text
clean
partial
stale
conflicted
unavailable
trade_candidate
```

除 unavailable 新增 `industry_context` 外，不允许无授权 wire change。

## 7.18 Skill update

`a-stock-monitor/SKILL.md` 只增加一句：

> `monitor-snapshot --json` 输出是 `monitor-v1` machine contract；状态、动作、缺口和停止条件只从结构化字段读取，不从自然语言重建。

不要复制 schema。

## 7.19 Tests

新增：

```text
tests/test_monitor_contract.py
```

至少覆盖：

```text
valid clean
valid partial
valid unavailable
unknown additive field accepted
missing required rejected
invalid container type rejected
bool schema version rejected
bool-as-int and int-as-bool rejected
unsupported version rejected
timezone-naive as_of rejected
NaN / Infinity rejected
invalid status
quote_coverage invalid
complete coverage consistency
industry_context validation
non-complete + no_action rejected
trade candidate without trade escalation rejected
confirmation mismatch rejected
industry data-gap invariant
manifest writes=true rejected
manifest/top stop_reason mismatch rejected
loads/dumps round-trip
```

## Done

```text
[x] monitor_contract.py 是 protocol owner
[x] commands_monitor 不维护平行 validation vocabulary
[x] unavailable shape 统一
[x] CLI 的 monitor snapshot 输出统一 contract serialization
[x] wire compatibility 有回归测试
```

---

# 8. Phase 4 — Explicit Framework Routing Catalog

**仓库：** `a-stock-agent-skills`

## 8.1 当前问题

`domain.py` 仍有：

```python
from a_stock_agent_runtime import checklist  # noqa: F401
```

仅用于：

```text
触发 checklist import
→ _register(...)
→ FRAMEWORK_REGISTRY populated
```

## 8.2 重新定义边界

`FrameworkMetadata` 当前混合：

### Routing / portfolio metadata

```text
portfolio_label
industry_keywords
stop_loss_pct
```

### Checklist presentation metadata

```text
checklist_name
subjective_items
skipped_items
checklist_definitions
custom_builder
```

本轮只把 routing/portfolio metadata 抽成显式 catalog。

## 8.3 新模块

新增：

```text
src/a_stock_agent_runtime/framework_catalog.py
```

最小模型：

```python
@dataclass(frozen=True)
class FrameworkRouting:
    key: str
    portfolio_label: str
    industry_keywords: tuple[str, ...]
    stop_loss_pct: tuple[float, float] | None
```

定义：

```text
FRAMEWORK_ROUTING
```

包含 A-F。

## 8.4 Authoritative routing values

先写回归测试锁住当前：

```text
key
portfolio_label
industry_keywords
stop_loss_pct
```

再迁移。

禁止改变：

```text
industry mapping
stop-loss coefficient
default routing
```

## 8.5 domain migration

`domain.infer_framework()` 和 `domain.get_stop_loss_pct()` 只读取 `framework_catalog`。

删除 side-effect import。

## 8.6 FrameworkMetadata cleanup

迁移后审计：

```text
portfolio_label
industry_keywords
stop_loss_pct
```

所有 caller。

若无人依赖，从 `FrameworkMetadata` 删除这些字段并删除 checklist 中的重复值。

如仍有 caller，先迁移到 catalog。

目标：routing values 只有一个 executable owner。

## 8.7 FRAMEWORK_REGISTRY

Checklist 自身可以暂时保留 `FRAMEWORK_REGISTRY` 用于 presentation metadata。

本轮不要求消灭整个 checklist registry。

关键验收：

```text
domain/runtime routing 不再依赖 registry side effect
```

## 8.8 Tests

更新：

```text
tests/test_import_graph.py
```

至少：

```text
domain.py 不 import checklist
import domain before checklist works
routing catalog contains A-F
routing catalog values unchanged
infer_framework before checklist import works
get_stop_loss_pct before checklist import works
```

## Done

```text
[x] domain 不依赖 checklist import side effect
[x] routing metadata 单一 owner
[x] routing / stop-loss 行为不变
[x] checklist presentation registry 可独立存在
```

---

# 9. Phase 5 — E2E Provenance Hardening

当前真实 E2E 已完成，本 Phase 不增加 scenario。

## 9.1 Capture artifact additive fields

保留现有字段，新增：

```text
repository_head
capture_source_sha256
skill_sha256
exposed_tools
isolation
```

## 9.2 repository_head

capture 时执行：

```bash
git rev-parse HEAD
```

## 9.3 capture_source_sha256

对：

```text
scripts/capture_agent_tool_e2e.mjs
```

计算 SHA256。

Offline test 必须核对。

## 9.4 Individual Skill hashes

保留 combined `source_skills_sha256` 兼容，同时新增：

```json
"skill_sha256": {
  "a-stock-research": "...",
  "a-stock-monitor": "..."
}
```

## 9.5 exposed_tools

记录：

```json
"exposed_tools": [
  "a_stock_cache",
  "a_stock_fetch",
  "a_stock_write"
]
```

Unauthorized W1 的证据变成：

```text
write tool available
+
write tool not called
```

## 9.6 Structured isolation

将自由文本 isolation 改成：

```json
{
  "home_isolated": true,
  "production_astock_tools_exposed": false,
  "market_data_network_used": false,
  "production_database_used": false,
  "model_credentials": "read_only"
}
```

不要把模型提供方网络和 A-stock/market-data 网络混为一谈。

## 9.7 Offline verifier

新增验证：

```text
repository_head format
capture script hash
individual Skill hashes
exposed tools
isolation flags
actual calls unchanged
a_stock_write exposed but absent from calls
```

## 9.8 Commit ordering and recapture

为避免 `repository_head` 指向不包含 capture script 的旧提交，按两步提交：

```text
1. 提交并 push capture script、Skill 和 offline verifier 的 source changes
2. 从 clean HEAD 执行 capture，再单独提交 fixture
```

本轮 source commit 为 `76c66a32d4c80559bd4df3b26091f95e1b99bccc`。随后执行：

```bash
timeout 300 node scripts/capture_agent_tool_e2e.mjs \
  tests/fixtures/agent_tool_e2e_live.json
uv run pytest tests/test_agent_tool_e2e.py -q
```

Verifier 确认 recorded commit 存在于当前历史、capture script 和 individual Skills 与该 commit 一致，并验证当前文件 hash。CI checkout 使用 `fetch-depth: 0`。Live recapture 不进入普通 CI；普通 CI 只验证 fixture。

既有八场景 Hermes artifact 保留为历史 capture，继续验证其自带 source/prompt/session/hash 证据；它不伪装成当前 Skill snapshot。当前 Monitor Skill 的精确绑定由本轮 live fake-tool fixture 负责。

## Done

```text
[x] capture 绑定 source commit
[x] capture 绑定 capture script
[x] capture 绑定 individual Skills
[x] fake W1 tool 明确暴露但未调用
[x] isolation metadata 可机器验证
```

---

# 10. Phase 6 — Runtime Contract Architecture Docs

新增：

```text
docs/architecture/runtime-contracts.md
```

只写当前态：

```text
decision-v1
monitor-v1
a-stock-lib deterministic owner
agent runtime application owner
framework routing catalog
Thin Skill role
live Agent E2E capture
offline verifier
```

明确三个版本维度：

```text
package_version
contract_version
policy_version
```

完成后示例：

```text
a-stock-lib package = 0.8.0
a-stock-agent-skills package = 0.1.13
decision contract = v1
monitor contract = v1
framework policy = RULE_VERSION / rule_hash
regulatory policy = rule metadata + freshness
```

---

# 11. 验证矩阵

## a-stock-lib

```bash
uv run pytest -q
uv build
python scripts/check_published_version_identity.py
git diff --check
```

CI 必须执行 guard。

## a-stock-agent-skills

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
uv run python scripts/check_regulatory_freshness.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
git diff --check
```

最终：

```bash
bash scripts/check.sh
```

普通 pytest 应覆盖：

```text
test_monitor_contract.py
test_agent_tool_e2e.py
```

---

# 12. 实际 Commit Ledger

## a-stock-lib

```text
39afda1 chore(deps): Track development lock
f7fd9df test(release): Guard published identity
```

package version 保持 `0.8.0`，未重新发布。

## a-stock-agent-skills

```text
bd9b4ad chore(version): Start runtime 0.1.13
7e46442 feat(contract): Extract monitor-v1
14b7a30 refactor(framework): Add routing catalog
76c66a3 test(agent): Harden capture provenance
52702ee test(agent): Record provenance capture
311be86 docs(architecture): Document runtime contracts
266cd5e fix(test): Preserve historical Agent evidence
```

Capture source 与 fixture 分为两个 commit，确保 fixture 的 `repository_head` 指向已经包含 capture script 和当前 Skills 的 clean commit。

---

# 13. Final Acceptance

只有全部满足才可输出 `COMPLETE`。

## Release drift

```text
[x] v0.8.0 non-wheel master changes 通过 guard
[x] package source drift 在 version 未变时失败
[x] guard 无网络依赖
```

## monitor-v1

```text
[x] contract owner 独立于 commands_monitor
[x] v1 wire names 未重命名
[x] unavailable snapshot 包含 industry_context
[x] monitor snapshot serialization 走 dumps_monitor_snapshot
[x] cross-field invariants 有测试
```

## Framework routing

```text
[x] domain.py 无 checklist side-effect import
[x] routing metadata 单一 owner
[x] infer_framework import-order independent
[x] stop-loss behavior unchanged
```

## E2E provenance

```text
[x] actual fake-tool calls 仍为预期序列
[x] repository_head recorded
[x] capture script hash recorded
[x] individual Skill hashes recorded
[x] write tool exposed
[x] write tool not called
[x] isolation fields machine-readable
```

## Safety

```text
[x] production DB untouched
[x] real holdings untouched
[x] cron untouched
[x] no real W1
[x] no TuShare/market-data credentials used in Agent E2E
[x] no unrelated large refactor
```

---

# 14. Implementation Evidence

```text
Overall status: COMPLETE

Implementation heads before this archival document commit:
a-stock-lib/master: f7fd9df1bf3cf88148019cd0d1ed4aa5c46d5367
a-stock-agent-skills/master: 266cd5e384fe859fe5e7a19d619d716555499947

Package versions:
a-stock-lib: 0.8.0
a-stock-agent-skills: 0.1.13

Pinned lib artifact:
version: 0.8.0
url: https://github.com/on195594/a-stock-lib/releases/download/v0.8.0/a_stock_lib-0.8.0-py3-none-any.whl
sha256: a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310

Contracts:
decision: v1
monitor: v1

Release drift guard: PASS
Framework catalog: PASS

Agent tool E2E:
provider: openai-codex
model: gpt-5.6-sol
repository_head: 76c66a32d4c80559bd4df3b26091f95e1b99bccc
capture_source_sha256: 8e4ecc9a4a013ed3fc87d5096cc2132324ff63904dcd350eb7f2bb20f2d16ed9
research calls: holdings -> fetch -> check
monitor calls: monitor-snapshot
unauthorized W1 calls: monitor-snapshot only; exposed a_stock_write not called

Tests:
- a-stock-lib full pytest -> 178 passed
- published identity focused tests -> 9 passed
- changed Agent focused suites -> 227 passed
- hosted a-stock-agent-skills scripts/check.sh -> 1039 passed, 2 skipped
- both repository CI heads -> success

Production impact:
DB touched: no
holdings touched: no
cron touched: no
real W1 executed: no
market-data credentials used: no

Remaining risks:
- historical eight-scenario Hermes evidence remains bound to its original capture hashes; current Monitor Skill binding is owned by the live fake-tool fixture

Rollback:
- a-stock-lib -> git revert f7fd9df 39afda1
- a-stock-agent-skills -> git revert 266cd5e 311be86 52702ee 76c66a3 14b7a30 7e46442 bd9b4ad
```

---

# 15. 本轮结束后的下一阶段

本 Spec 完成后才重新评估：

```text
commands_monitor.py
commands_holdings.py
fetcher.py
```

下一阶段建议：

```text
monitor-v1 stable
        ↓
extract monitor snapshot builder
        ↓
extract monitor source adapters
        ↓
then evaluate holdings split
```

不要直接开始全仓 DDD。

最终原则：

> **Stable contracts first. Explicit ownership second. Module movement last.**

---

# 16. 实施复盘

## 16.1 结果

本轮按修订后的 Spec 完成全部 P0/P1 工作，最终代码实现停在 `a-stock-lib/f7fd9df` 与 `a-stock-agent-skills/266cd5e`；随后仅追加架构、实施证据和本 Spec 归档。两仓库对应 CI 均通过，没有生产部署或状态写入。

## 16.2 做得好的部分

- 先冻结 monitor-v1 wire shape，再移动 validator 与 routing owner，没有改变投资阈值或 W1 授权模型。
- Drift guard 使用 stdlib 与临时 Git 仓库测试，保持离线且不引入依赖。
- Framework catalog 复用既有 A–F exhaustive regression，避免重新设计行业映射和止损系数。
- Live E2E 在单个真实模型会话中暴露 fake write tool，以“可调用但未调用”证明未授权 W1 被阻止。
- Capture source 与 fixture 分开提交，解决 `repository_head` 的自引用问题。

## 16.3 偏差、根因与修复

### 旧 development lock 阻断 branch guard

初始 `a-stock-lib/uv.lock` 未跟踪且仍声明 `0.7.0`。直接忽略会让本地 `uv` 与 CI 使用不同解析结果，因此将 lock 更新为 `0.8.0` 后提交，而不是用 `.gitignore` 隐藏。

### 原 drift 设计漏掉 commit 前变化

原文只比较 `tag..HEAD`，无法在 direct-to-master 的 pre-commit gate 中发现 staged、unstaged 或 untracked package drift。实现改为合并四类变化，并增加对应回归测试。

### Monitor Skill 修改触发历史 Hermes evidence 失败

Phase 3 增加 monitor-v1 说明后，旧 Hermes artifact 的测试仍要求其历史 Skill hash 等于当前 Skill，导致一次 hosted CI 失败。该 artifact 的 capture commit 不在当前 master ancestry，不能伪造为当前 snapshot，也不能在未部署 Hermes Skill 的情况下安全重跑。

最终处理：保留八场景 artifact 自带的历史 hash、prompt、session 与 runtime provenance；当前 Skill 的精确 source binding 由新的 live fake-tool fixture 承担。后续修改任何 Skill 前，先搜索所有 `skill_sha256` consumer，区分历史证据与 current-head gate。

### 本机 full gate 间歇超时

本机完整 pytest 曾在文件系统等待中超时，但 focused suites 正常，GitHub runner 上同一 `scripts/check.sh` 完成 `1039 passed, 2 skipped`。因此超时记录为环境证据，不被误报成测试失败；最终接受以 exact-head hosted CI 为准。

## 16.4 文档对齐

- 本 Spec 已从 `AUTHORIZED FOR IMPLEMENTATION` 更新为 `IMPLEMENTED / COMPLETE`，并记录实际 commit、测试和安全结果。
- `docs/architecture/runtime-contracts.md` 描述 decision-v1、monitor-v1、routing owner 和三个独立版本维度。
- `README.md` 与 `docs/CHANGELOG.md` 已对齐 package `0.1.13`、monitor-v1、framework catalog 和 E2E provenance。
- `docs/README.md` 已索引本 Spec 与 runtime contract 架构文档。

## 16.5 后续原则

当前没有必须补做的 blocker。只有在 monitor-v1 稳定运行并出现可度量维护问题后，才评估 snapshot builder/source adapter 抽取；不要提前拆分 `commands_holdings.py`、`fetcher.py` 或引入新的 schema/DDD 层。
