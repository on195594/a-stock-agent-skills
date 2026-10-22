# 风险分母与超限归因规范（2026-10-22）

状态：approved for implementation
用户授权：2026-10-22 用户在 A/B/C/D 方案中明确选择“B+D”。

## 问题

2026-10-12 → 10-15 长江电力（600900）始终持有 800 股，单股止损风险却从
5.86% 升到 9.2% 并“超限”，随后被建议减仓。原因：

1. 分母只用券商截图总资产，从 118,577 元降到 75,911 元，主要是资金转出，
   而不是亏损；规则原本就把分母定义为“股票市值 + 本策略可动用现金”。
2. 超限明细只给总金额，不说明其中多少是浮盈回吐。原止损锚定在成本上，股价
   越涨风险数越大，容易被误读成“该卖盈利仓”。

被否决的方案 A（止损随浮盈上移）：在 13 只股票、1,639 个月度建仓样本上回放
（复权价，3 年期，T+1 收盘执行），所有上移变体的平均收益都低于固定止损
（56.4% → 21%–54%），最差 10% 分位只从 −26.1% 改善到约 −25%；能改变长电
风险数的只有从建仓起就跟踪的变体，而它们表现最差。样本存在幸存者偏差，
且止损后不再买回；该回放只是否决依据，不证明现行止损有效。

## 规则

- **B 分母**：个人风险政策文件可选 `off_account_strategy_cash`（CNY，有限且
  `>= 0`），指仍用于本策略、但放在券商账户外的现金。提供 `--portfolio-value`
  时，分母 = 账户资产 + 该值；没有 `--portfolio-value` 时它不能单独构成分母。
  资金转回账户时须同步修改政策文件，避免重复计入。
- **D 归因**：单股止损风险拆为
  `unrealized_gain = 股数 × max(现价 − max(reference_cost, 第二档止损), 0)`，
  其余是本金部分（`reference_cost` 与第二档止损之间）。超限明细列出两部分金额、
  分母数值及来源；任一持仓缺少参考成本时，组合级归因标为 unknown。
- 风险公式、2%/8% 兼容默认、个人上限和严格 `>` 判定不变。超限仍只冻结新增
  风险并触发复核；快照未给出的卖出标的、顺序或股数，模型不得提出。

## 契约

- `account.denominator_components`：`{account_value, off_account_strategy_cash}`；
  无分母时为 null。`manifest.denominator_source` 为 `cli` 或 `cli+policy_file`。
- `holdings[].stop_risk_unrealized_gain`：数值或 null。
- `account.risk_policy` 带有 `off_account_strategy_cash` 时，在 `field_sources`
  中标为 `policy_file`。
- 均为新增字段；现有 monitor-v1 必填字段与校验不变。

## 验证

`tests/test_risk_policy.py`：两个 CLI 的分母扩展、非法值 fail-closed、无分母
不构造、归因拆分（含长电 10-15 数值）、未知归因；三处实现均做过互变检查
（mutation check）。
