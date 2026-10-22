# P0 监管门证据按年报期沿用规范（2026-10-22）

状态：approved for implementation
用户授权：2026-10-22 用户在三个方案中选择“(3) 只修刷新被清空”。

## 问题

`a-stock-fetch fetch` 重写整份基本面缓存时，把 `regulatory_gate` 重置为
`incomplete`（来源 unavailable），已补的官方证据随之丢失；而证据唯一写入口
`set` 需要整份重写基本面。结果是所有持仓的 P0 永远 `incomplete`，监控每次都
“证据不足”。

## 规则

- 已补证据（整体 `clear` 或 `blocked`）在**年报期不变**（保存的事实
  `report_period` 等于当前 `data_period`）时，刷新后继续沿用；出现更新的
  年报期后失效，须重补。
- 沿用时用保存的原始事实（`regulatory_gate.evidence_facts`）按当前规则重新
  判定：阈值变化、规则版本过期、来源非官方、板块证据缺失都会改变结果；
  `blocked` 同样沿用，不会因刷新被降成 `incomplete`。没有原始事实的旧证据不沿用。
- 沿用在 `set_fundamentals` 的同一写事务内读取最新 P0 证据，刷新不会覆盖
  并发补录的证据。
- `incomplete` 不沿用；来源要求、“未搜到负面不得判 clear”、各子门判定逻辑
  和主板/科创创业/北交所口径都不变。
- 新增 W1 `regulatory-evidence <代码>`：从 stdin 读事实 JSON，由 runtime 计算
  门状态并合并进当前缓存；只接受事实字段，带预设子门对象（如 `listing_risk`）
  的输入被拒绝；`report_period` 必须等于缓存的 `data_period`；不改
  `updated_at`，不让其他基本面字段显得更新。

## 已知并接受的风险

上市风险（ST/退市）和立案调查是事件型的。年报期内若新出现风险警示或立案，
沿用的证据不会自动失效；依赖监控的公告与 L3 治理条件复核发现，发现后重补
`blocked` 证据。

## 修复

显式 JSON `null` 的 `listing_status`/`investigation_status` 原先被 `str()` 成
“none”并判为无风险（fail-open），现按缺失证据处理。

## 独立审查（Codex，2026-10-22）

首轮发现 5 项 Important、1 项 Minor：预设子门可绕过事实判定、沿用只复制旧结论、
刷新可覆盖并发补录、分红提示命令按当前股数计算、已记账纯转增被误报、组合归因
在风险未知持仓存在时误报已知。均已修复并各有回归与互变检查。复审确认 6 项中 5 项
FIXED、转增匹配 PARTIAL，并新发现：现金/转增只记一部分时提示命令会重复入账
（Important）、沿用后 fetch 摘要少计完整门（Minor），均已修复。

## 验证

`tests/research/test_p0_evidence_carry_forward.py`：同年报期沿用 clear/blocked、
新年报期与 incomplete 不沿用、规则过期仍 fail-closed、命令合并且不改
`updated_at`、跨期证据被拒、未确认不写、null 不再 fail-open；沿用路径与期间
判断均做互变检查。
