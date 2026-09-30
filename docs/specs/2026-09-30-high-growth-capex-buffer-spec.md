# A股 Research 制造业高成长资本开支弹性缓冲规范（2026-09-30）

状态：approved for implementation
用户授权：2026-09-30 用户明确确认“同意”基于审查结论实施风控修复

## 背景与问题

2026-09-30 对立讯精密（002475）分析实测中，公司呈现优秀盈利能力（ROE 3年均值 21.35%，2026H1 净利同比 +18.04%）与良性造血能力（TTM CFO +165.37 亿元），但因近年果链自动化扩产及汽车电子/通信连接器垂直整合并购，TTM 资本开支达到 186.46 亿元，`CAPEX / CFO = 1.13`。

现有 P2 自由现金流门（`cash_flow_gate`）对非 C/D 框架采取机械一刀切策略：凡 `capex > cfo` 一律判定 `status: blocked`，`capex_redline: breached`。这导致处于重资产扩张期的高 ROE 制造龙头被系统性一票否决，无法形成买入评级与仓位矩阵。

## 目标与原则

1. 保持现有测试与默认行为 100% 向后兼容：在未显式提供 `a_capex_review` 时，`capex > cfo` 仍严格保持 `status: blocked`；
2. 为 A通用框架（及制造业高成长白马）建立结构化的资本开支复核机制 `a_capex_review`，对齐 C/D 框架的 `cd_capex_review`；
3. 设立严格的量化准入门槛，杜绝垃圾公司借扩产之名虚饰现金流失血：
   - 必须通过造血红线（`cfo > 0`）；
   - ROE_TTM 必须 `>= 15.0%`（证明投入资本具备创造超额回报能力）；
   - `CAPEX / CFO <= 1.25`（扩张开支不得超出经营造血的 1.25 倍）；
   - 开支类型必须限定为扩产、并购、产能扩张或技术升级；
   - 必须具备官方/财报正式证据来源。
4. 条件全部满足时，`status` 判定为 `clear`，`action_eligible: true`，`capex_redline: reviewed_expansion`。

## 契约定义

在 `risk_gates.cash_flow_gate` 中，当 `framework in {"A通用", "A"}` 且 `capex > cfo` 时：
- 若未提供 `a_capex_review`：维持原判定 `status: blocked`, `reason_code: capex_exceeds_cfo`；
- 若提供 `a_capex_review`：
  - 必填字段：`capex_type`, `roe_ttm`, `expansion_rationale`, `sources`；
  - `capex_type` 枚举：`{"expansion", "acquisition", "capacity_expansion", "tech_upgrade", "扩产", "并购", "产能扩张", "技术升级"}`；
  - 门槛：`roe_ttm >= 15.0` 且 `capex / cfo <= 1.25`；
  - 达标输出：`status: clear`, `action_eligible: true`, `reason_code: a_capex_review_clear`, `capex_redline: reviewed_expansion`；
  - 超标输出：`status: blocked`, `reason_code: a_capex_roe_below_threshold` 或 `a_capex_ratio_above_1_25`；
  - 缺失输出：`status: incomplete`, `reason_code: a_capex_review_incomplete`。
