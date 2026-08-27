# L3 Materiality and Thesis Versioning Repair Spec

Date: 2026-08-27
Status: implemented and deployed on 2026-08-27; production thesis rewrite verified
Owner: a-stock-monitor / shared runtime

## 1. Incident

华东医药旧论文把“医美收入连续两个季度下滑”定义为集团级论文破灭并预设清仓。2026H1披露后，该条件机械成立，但医美仅占集团收入2.95%，同期集团扣非净利润同比+5.44%、经营现金流同比+1.73%、医药工业扣非净利润同比+13.35%、创新产品收入同比+52%。系统据此建议清仓800股，暴露出三个根因：

1. L3没有结构化区分集团核心驱动、非核心分部、治理红线和普通预警；
2. L3动作没有结构化区分复核、减仓和清仓，旧自由文本可把非核心分部恶化直接升级为全仓退出；
3. L3没有退役/被新论文取代的生命周期，当前CLI只能把旧条件伪装成`not_triggered`或继续保留为活动条件，无法安全重写论文。

这不是“低位不应止损”的价格例外。缺陷是**触发条件与动作幅度没有经过论文范围和重要性约束**；价格高低不能豁免有效规则，但无效或已被取代的规则也不能继续获得交易权。

## 2. Non-goals

- 不撤销用户已经真实执行的历史交易；
- 不把低估值设为任何L3的自动豁免；
- 不允许模型在触发后以主观“好公司”叙事临时改判；
- 不自动下单，不修改券商状态；
- 不改变价格止损、Tier、估值退出和交易所申报规则；
- 本spec本身不授权生产DB schema、runtime、持仓或Skill写入。

## 3. Corrected decision model

### 3.1 Active-thesis invariant

只有绑定到当前活动论文版本的活动L3条件可以产生交易建议。旧论文和旧L3必须保留审计记录，但不得参与当前触发、预警计数或动作优先级。

### 3.2 Structured scope and action

每条新L3必须显式存储：

- `condition_scope`: `aggregate | core_driver | non_core | governance`
- `action_level`: `review | reduce | exit`
- `materiality_basis`: 可复核的利润、现金流、资产负债表、治理或核心驱动依据
- `temporary_exit_rule`: 明确条件、动作幅度和下一复核节点

约束：

1. `non_core`不得直接配置`exit`；最多`review`，若与集团指标共同恶化可在新证据下升级为新的`aggregate/core_driver`条件，但不得复用原条件偷渡清仓。
2. `governance`可配置`exit`，但必须是资金占用、违规担保、财务造假、管理层诚信被确定性证据否定等集团级事实。
3. `core_driver`配置`exit`时，必须在`materiality_basis`中声明其为何构成当前论文的主要利润/现金流来源，并声明所需确认期数。
4. `aggregate`配置`exit`时，必须使用集团或主要利润引擎的盈利、现金流、资产负债表指标，不得只使用价格或非核心分部收入。
5. 机械规则的“不得事后追加例外”仍保留，但只在确认条件属于**当前活动论文、字段完整、scope/action合法**之后适用。

### 3.3 Pre-execution semantic gate

任何`triggered + reduce/exit`动作输出前必须检查：

- 条件绑定当前活动论文版本；
- 条件未退役；
- scope/action组合合法；
- materiality_basis可追溯；
- 动作幅度和交易所可申报股数已定义；
- 证据报告期与条件要求一致。

任一失败：输出“触发文本成立，但交易契约无效/已过期，冻结交易并重做论文”，不得输出卖出股数。该门是规则有效性检查，不是价格或基本面事后豁免。

## 4. Minimal data model

### 4.1 New table `holding_thesis_versions`

- `id INTEGER PRIMARY KEY`
- `holding_id INTEGER NOT NULL`
- `version INTEGER NOT NULL`
- `l1 TEXT NOT NULL`
- `l2 TEXT NOT NULL`
- `rewrite_reason TEXT NOT NULL`
- `status TEXT NOT NULL CHECK(status IN ('active','superseded'))`
- `created_at TEXT NOT NULL`
- unique `(holding_id, version)`
- at most one active version per open holding

### 4.2 Extend `holding_l3_conditions`

Add nullable/auditable columns without deleting old rows:

- `thesis_version_id INTEGER`
- `is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))`
- `retired_at TEXT`
- `retired_reason TEXT`
- `condition_scope TEXT` with values above plus `legacy_unclassified`
- `action_level TEXT` with values above plus `legacy_unclassified`
- `materiality_basis TEXT`

Existing rows migrate to `legacy_unclassified` and remain visible under `--all`. The semantic gate is enabled **per holding only after that holding has an active `holding_thesis_versions` row**. Holdings not yet rewritten keep their pre-migration L3 behavior with a visible `legacy contract` warning, so deployment does not create a cross-portfolio stop-loss vacuum. A rewritten holding may not retain any active `legacy_unclassified` L3: `thesis-rewrite` must retire or classify every active legacy row for that holding before commit.

This is an incremental cutover boundary, not a permanent exemption. Each remaining holding must be rewritten or classified through a separately reviewed user decision; runtime deployment itself must not silently reinterpret other positions.

## 5. CLI contract

Add one atomic W1 command:

```text
a-stock-cache --confirm-write thesis-rewrite <code>
```

It reads one JSON object from stdin:

```json
{
  "l1": "...",
  "l2": "...",
  "rewrite_reason": "...",
  "retire_l3_ids": [7, 8],
  "new_l3": [
    {
      "condition": "...",
      "scope": "core_driver",
      "action": "reduce",
      "materiality_basis": "...",
      "temporary_exit_rule": "..."
    }
  ]
}
```

The command must, in one SQLite transaction:

1. verify one open holding exists;
2. verify every retired L3 belongs to that holding and is active;
3. supersede the prior active thesis version, if any;
4. insert the new thesis version;
5. retire the named old L3 rows with reason/time;
6. insert the new L3 rows linked to the new thesis version;
7. commit only if every validation succeeds.

`l3-list <code>` defaults to active conditions. `l3-list <code> --all` shows retired rows and thesis version. `l3-update` rejects retired rows. No transaction event, shares, cost, buy_date, reference_cost or realized P/L may change.

## 6. Proposed current thesis for 华东医药 000963

This is a candidate payload, not yet a production write.

### L1 — why the company can create value

华东医药当前集团价值不再由“医药流通+医美双轮”定义。主要利润引擎是中美华东医药工业及其创新药商业化能力；浙江省医药商业网络提供渠道和现金流底座。2026H1医药工业收入79.69亿元同比+8.92%、扣非净利润17.25亿元同比+13.35%；创新产品收入16.84亿元同比+52%、占医药工业收入21.14%。医美收入只占集团2.95%，应视为修复期可选项，不是集团论文的一票否决项。

### L2 — why the current position remains worth underwriting

截至2026-08-27，当前价约27.42元，PE_TTM约13.9倍，静态PE近5年分位0.3%、PB近10年分位0.2%。市场已对集采、医美和低增长给出明显折价。继续持有的赔率来自：资产负债率约35.5%、毛利率长期稳定在32%—34%、经营现金流为正；创新药收入增长可能在未来12—24个月逐步覆盖成熟集采品种流失。核心风险不是医美单项下降，而是创新业务替代速度是否跑赢未中选集采品种的收入和利润流失。

### New L3 set

1. **创新替代失败（core_driver / reduce）**
   Condition: 连续两个可比的半年报/年报披露期同时满足：医药工业收入同比≤0、医药工业扣非净利润同比≤0，且创新产品收入同比<20%或创新产品占医药工业收入跌破18%。季报未披露中美华东分部扣非净利润或创新产品收入时，本条件必须保持`pending`，不得用集团单季指标或管理层口径代填。
   Materiality: 医药工业是主要利润引擎；创新替代是当前重估论文核心。
   Action: 首次确认后减持1/3 `initial_shares`并在下一可比完整披露期复核；若第三个连续可比完整披露期仍全部满足，清仓剩余持仓。

2. **集团现金盈利恶化（aggregate / reduce）**
   Condition: 连续两个披露期集团扣非归母净利润同比<0，且每期同时满足以下任一TTM现金盈利条件：① TTM归母净利润≤0；② TTM经营活动现金流净额<0；③ TTM归母净利润>0且TTM经营活动现金流/TTM归母净利润<0.8。禁止在净利润≤0时计算现金流/利润比值，避免负数除法反转。
   Materiality: 同时约束利润方向和现金兑现，避免单一非经常项或资本化会计处理误判。
   Action: 将目标持仓降至`initial_shares`的50%；若下一披露期TTM经营现金流仍<0且扣非净利润继续同比<0，清仓。

3. **重大治理或资产负债表破坏（governance / exit）**
   Condition: 控股股东非经营性资金占用、违规担保、财务造假/重大诚信事件被正式文件确认；或单期新增商誉/长期资产减值超过上一完整年度归母净利润的20%，且对应资产组经营亏损仍未止住。
   Materiality: 集团级资本永久损失或治理可信度破坏。
   Action: 确定性证据确认后清仓。

### Non-L3 alerts

- 医美收入继续同比下降：`holding_deterioration`黄色预警，跟踪Sinclair止亏和商誉；不得单独授权清仓。
- 4个未中选集采品种院内收入流失：黄色预警；其交易含义由“创新替代失败”和“集团现金盈利恶化”两条L3共同裁决。

## 7. Current action under the candidate thesis

As of 2026H1 all three new L3 conditions are `not_triggered`:

- 医药工业收入+8.92%、扣非净利润+13.35%、创新产品收入+52%、占比21.14%；
- 集团扣非净利润+5.44%、经营现金流+1.73%，现金流为正；
- 无资金占用、无违规担保，商誉占总资产约7.1%，未见满足20%年度净利润门槛的新增减值。

Therefore the candidate thesis implies **hold, no forced sale**. Portfolio risk and concentration remain separate; the thesis rewrite does not authorize adding shares.

## 8. Acceptance tests

### RED

1. Legacy non-core L3 with free-text “triggered→clear” currently remains action-capable and cannot be safely retired.
2. No command can atomically version L1/L2, retire old L3 and add replacement L3.

### GREEN

- migration is idempotent on empty fixture and legacy fixture;
- `thesis-rewrite` is W1 and fails with exit 3 without `--confirm-write` before opening a write transaction;
- invalid/mixed-holding `retire_l3_ids` rolls back every change;
- default `l3-list` returns only active conditions; `--all` preserves retired audit rows;
- `l3-update` rejects retired rows;
- 已有活动论文版本的持仓中，legacy-unclassified `triggered` rows cannot emit a reduce/exit action；尚未迁移论文的其他持仓继续旧行为并显示`legacy contract`警告，不得出现止损真空；
- current 000963 fixture retires #7/#8 and creates exactly one active thesis version plus exactly three active L3 conditions;
- holdings shares=800, costs, buy_date and event count remain byte/row equivalent before and after thesis rewrite;
- `remove-holding` lifecycle cleanup covers the new thesis table;
- `scripts/check.sh`, focused migration/CLI tests, Ruff, validator and `git diff --check` pass.

## 9. Rollback

- Code rollback: revert the bounded commit and redeploy the prior runtime wheel/version.
- Data rollback: restore the verified pre-migration SQLite backup; do not manually reactivate old L3 rows after partial failure.
- Stop conditions: any share/event/cost drift, migration non-idempotency, cross-holding retirement, or action from a retired/legacy-unclassified L3 blocks deployment.
