# P0 监管门证据按年报期沿用规范（2026-10-22）

状态：approved for implementation
用户授权：2026-10-22 用户在三个方案中选择“(3) 只修刷新被清空”。

## 问题

`a-stock-fetch fetch` 重写整份基本面缓存时，把 `regulatory_gate` 重置为
`incomplete`（来源 unavailable），已补的官方证据随之丢失；而证据唯一写入口
`set` 需要整份重写基本面。结果是所有持仓的 P0 永远 `incomplete`，监控每次都
“证据不足”。

## 规则

- 已补证据（整体 `clear` 或 `blocked`）在**年报期不变**（四个子项的
  `report_period` 都等于当前 `data_period`）时，刷新后继续沿用；出现更新的
  年报期后失效，须重补。
- 沿用时按当前规则重新判定：规则版本过期、来源非官方、板块证据缺失仍然
  fail-closed；`blocked` 同样沿用，不会因刷新被降成 `incomplete`。
- `incomplete` 不沿用；来源要求、“未搜到负面不得判 clear”、各子门判定逻辑
  和主板/科创创业/北交所口径都不变。
- 新增 W1 `regulatory-evidence <代码>`：从 stdin 读事实 JSON，由 runtime 计算
  门状态并合并进当前缓存；`report_period` 必须等于缓存的 `data_period`；不改
  `updated_at`，不让其他基本面字段显得更新。

## 已知并接受的风险

上市风险（ST/退市）和立案调查是事件型的。年报期内若新出现风险警示或立案，
沿用的证据不会自动失效；依赖监控的公告与 L3 治理条件复核发现，发现后重补
`blocked` 证据。

## 修复

显式 JSON `null` 的 `listing_status`/`investigation_status` 原先被 `str()` 成
“none”并判为无风险（fail-open），现按缺失证据处理。

## 验证

`tests/research/test_p0_evidence_carry_forward.py`：同年报期沿用 clear/blocked、
新年报期与 incomplete 不沿用、规则过期仍 fail-closed、命令合并且不改
`updated_at`、跨期证据被拒、未确认不写、null 不再 fail-open；沿用路径与期间
判断均做互变检查。
