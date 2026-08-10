你是独立的A股投资规则与Skill契约审查员。只审查下面的快照，不访问或修改任何文件，不调用工具。此变更已落到canonical仓库，且通过symlink同时影响Hermes active a-stock-monitor；审查必须严格、只读。

## 输出合同

- `Verdict`: `PASS` / `PASS_WITH_NOTES` / `REQUEST_CHANGES`
- `Blocking findings`: 每项给出快照证据、风险、最小修复；没有写“无”
- `Important notes`: 非阻塞项
- `Investment semantics`: 明确判断以下五点
  1. `股数 × max(现价−第二档止损价,0) ÷ 当前组合总资产`是否被准确描述为“从当前盯市净值持有到第二档线的潜在回撤”，而不是本金亏损或安全垫；
  2. 2%/8%超限禁止新增风险的既有语义是否被意外改变；
  3. 券商截图成本、经济回报现金流、`cost_price`、`reference_cost`边界是否自洽；
  4. 对账未完成时冻结成本比例派生交易、但允许同口径绝对L3线继续核验，是否足够fail-closed且不过度；
  5. 是否仍可能把第一档复查线与第二档止损线误判为冲突。
- `Test assessment`: 聚焦契约测试是否覆盖原误读和最近反向边界；不要要求新测试工程。
- `Recommended next step`: 恰好一个动作。

## 授权范围

用户明确授权修改`/home/lin/a-stock-agent-skills`中的Skill源码并让AGY复审。仓库规则要求：投资规则变更有dated spec、聚焦回归、只读复审；不得修改数据库schema、生产状态、cron、凭证、持仓或交易记录。

## 变更快照

### skills/a-stock-monitor/references/portfolio-risk.md

原文：
```md
### 风险预算

`单股风险贡献 = 股数 × max(现价 − 第二档止损价, 0) ÷ 可投资组合总资产`

- 默认单股上限2%、组合第二档止损风险合计上限8%；均为待回放验证的启发式默认值，
  用户有既定预算时以用户值为准；
- 任一单股或组合超限：禁止新增风险；
- 已跌破第二档的持仓单独标为“已破线”，不能因剩余风险为0显示正常。
```

修改后：
```md
### 风险预算

`单股当前净值回撤贡献 = 股数 × max(现价 − 第二档止损价, 0) ÷ 可投资组合总资产`

该指标衡量“若从当前市价持有到第二档止损线，当前组合净值可能回撤多少”，包含尚未
实现的浮盈回吐；它不是买入本金亏损，也不是现价距离止损线的“安全垫”。现价上涨会
增加等待至同一止损线时可能回吐的当前净值，不能据此把公式反向解释为风险下降。

- 默认单股上限2%、组合第二档止损风险合计上限8%；均为待回放验证的启发式默认值，
  用户有既定预算时以用户值为准；
- 任一单股或组合超限：禁止新增风险；
- 已跌破第二档的持仓单独标为“已破线”，不能因剩余风险为0显示正常。

### 券商成本与规则参考成本对账门

券商截图成本、`holdings.cost_price` 与 `holdings.reference_cost` 口径不同：券商成本只
用于复原截图账户盈亏；经济回报按不可变交易事件现金流计算；Tier 与框架止损使用
`reference_cost`。三者数值不同不自动证明任一方错误，也不得据此直接覆盖本地账本。

当券商截图成本与本地记录不一致时：

1. 先核对股数、买卖事件、费用税费、现金分红及除权送转记录；
2. 未完成对账前，成本比例派生的止损/Tier只可展示来源，不得授权对应交易；
3. 结构化L3中的绝对价格线仅在确认其与当前除权口径一致后才可执行，否则保持待核实；
4. C01须分别注明账户盈亏成本来源、规则参考成本来源及对账状态。
```

### skills/a-stock-monitor/SKILL.md

```diff
-| C01 | 组合风险 | 明确总资产分母；输出单股权重、单股止损风险、组合止损风险 |
+| C01 | 组合风险 | 明确总资产分母；输出单股权重、当前净值至第二档线潜在回撤、组合潜在回撤；成本口径不一致时输出对账状态 |
```

### tests/monitor/test_skill_contract.py

```py
PORTFOLIO_RISK = (ROOT / "references" / "portfolio-risk.md").read_text(encoding="utf-8")

def test_portfolio_risk_names_drawdown_and_fails_closed_on_cost_drift():
    assert "单股当前净值回撤贡献" in PORTFOLIO_RISK
    assert "它不是买入本金亏损，也不是现价距离止损线的“安全垫”" in PORTFOLIO_RISK
    assert "成本比例派生的止损/Tier只可展示来源，不得授权对应交易" in PORTFOLIO_RISK
    assert "账户盈亏成本来源、规则参考成本来源及对账状态" in PORTFOLIO_RISK
```

### dated spec增补

```md
## 组合回撤与成本来源澄清（2026-08-10）

用户在持仓截图分析及AGY只读复核后，明确授权修复canonical Skill源码。本批只修复
术语和成本来源门禁，不改变风险公式、2%/8%启发式阈值、框架系数或交易动作。

### 范围
1. 明确命名当前净值至第二档线潜在回撤，说明包含浮盈回吐，不是本金亏损或安全垫。
2. 券商截图成本与本地cost_price/reference_cost不一致时分别标明来源；对账前不授权成本比例派生交易。
3. 绝对L3价格线须确认除权口径一致；否则保持待核实。
4. 增加一个聚焦契约测试。

### 非范围
不修改runtime、数据库schema、生产状态、cron、凭证、持仓或交易记录；不新增回测、券商接口、成本同步器或阈值。
```

## 父级验证证据

- 聚焦：`uv run pytest -q tests/monitor/test_skill_contract.py` → `14 passed`
- Ruff：`uv run ruff check .` → `All checks passed!`
- Skill validator：`uv run python scripts/validate.py` → `skill validation passed`
- QA standalone：`python3 -I tests/qa/standalone_smoke.py` → `qa standalone smoke passed`
- `git diff --check` → passed
- 全量pytest：`605 passed, 1 skipped, 6 failed`。六项失败均位于未修改runtime/installer路径：四项旧测试期待⚠️/🔴但当前基线runtime输出🚨；两项installer内部`uv build`失败。本次修改仅markdown和一个契约测试，不得把这些失败伪装成本次通过，也不要要求在本审查中顺带修复。

请重点反驳自己的上一轮误读：上一轮把该公式当成“浮盈安全垫”并称逻辑颠倒、把长电第一档22.872与第二档21.313称为冲突、把8月25日复核日误当成清仓点。只有当前快照仍有真实问题时才给blocker。