# A股 Research incomplete/QA 与估值口径契约修复规范（2026-09-02）

状态：approved for bounded implementation
用户授权：2026-09-02 明确要求根据比亚迪研究复盘执行落地

## 问题

2026-09-02 比亚迪 `FUNDAMENTALS_HIT` 研究正确识别最新半年报 BPS 与年报口径缓存 PB 不兼容，并按 Research 主合同停止评分和仓位动作；但 QA 第9项仍要求输出 A/B/C/D 配置评级，将正确的 fail-closed 报告判为 `NON_COMPLIANT`。同一报告还漏写缓存中已有的股息率，QA 因无法区分“未展示”与“字段缺失”报 Minor。当前 fetcher 已同时持有当前价、年报 BPS 与 `latest_report_snapshot.fields.bps`，却未输出确定性的兼容性关系。

## 目标

1. 对齐 Research 与 QA：只有基本面评分必需输入缺失或最新报告基本面冲突导致 `scoring_status=incomplete` 时，才不得要求或编造配置评级；PB/BPS 估值口径冲突仅控制 timing，不得单独吞掉配置评级。
2. `FUNDAMENTALS_HIT` 报告必须先展示固定最小数据卡，避免已取得关键字段被正文遗漏。
3. 在现有 fetch/cache JSON 内增加只读 `valuation_compatibility` 派生字段，由确定性代码表达年报 PB 与最新报告 BPS 的关系。
4. 用本次故障类 fixture 证明正确 fail-closed 可通过 QA，同时无理由漏评级仍失败。

## 非目标

- 不改 A—F 阈值、权重、评分公式、双轨矩阵、L3、Tier、止损或仓位语义。
- 不新增行情/财务 Provider、依赖、数据库列、表或迁移。
- 不改真实持仓、交易事件、生产数据库、配置、cron 或凭证。
- 不引入新的 QA CLI、报告生成器、项目、缓存层或第二套评分器。
- 不修改 `a-stock-lib`；派生字段由已有 consumer runtime 数据完成。

## 契约

### 1. QA fail-closed 对齐

QA 第9项必须接受以下显式出口：

- `scoring_status=incomplete` 且报告列出基本面评分必需输入缺失或最新报告基本面冲突时，配置评级、时机评级、综合分和仓位矩阵均可标为 `not_formed`；报告须写明 recognized reason 与停止范围。
- 只有 `timing_status=incomplete`（包括 PB/BPS 估值口径不兼容）、但基本面机械评分完整时，仍必须输出配置评级；估值兼容性字段不得单独控制 `scoring_status`。
- 未声明合法 incomplete 原因而省略评级继续判 Important FAIL。

### 2. FUNDAMENTALS_HIT 最小数据卡

Research 报告合同要求基本信息之后列出：当前价/时点/来源、5日涨跌、PE与5年分位、PB与BPS各自口径、股息率与DPS、`latest_report_snapshot.report_period`、`fields.revenue_yoy`、`fields.net_profit_yoy`、`scoring_status`、`timing_status` 和缺失原因。字段有值时必须展示；顶层字段无值时展示 `missing` 与 `null_reasons`，nested snapshot 字段无值时展示其自身 `status`。不得凭正文省略推断缺失。`references/report-contract.md` 的评级、总分和仓位模块必须同步允许上述合法 `not_formed`，不得只修改 QA。

### 3. valuation_compatibility

在现有 fetcher cache payload 中新增一个结构化字段，不新增 DB schema：

```json
{
  "valuation_compatibility": {
    "pb_cache": 3.48,
    "pb_cache_bps": 24.9573,
    "pb_cache_bps_period": "2025年报",
    "pb_latest_report": 3.3,
    "latest_report_bps": 26.3208,
    "latest_report_period": "2026半年报",
    "relative_difference_pct": 5.17,
    "status": "period_mismatch",
    "timing_eligible": false,
    "reason_code": "different_period_value_mismatch",
    "reason": "latest report BPS changes current-price PB by more than 2%",
    "quote_source": "sina",
    "quote_as_of": "2026-09-02T11:30:00",
    "latest_report_bps_source": "tushare.fina_indicator+income+balancesheet",
    "latest_report_announcement_date": "2026-08-29"
  }
}
```

规则：

- `pb_latest_report = round(current_price / latest_report_bps, 2)`，使用 Python `round` 语义。
- `difference_for_gate = abs(pb_cache - pb_latest_report) / pb_cache * 100`；实现必须用 `Decimal(str(value))` 对已冻结的两位 PB 做十进制安全计算，门禁比较未再次取整的 `difference_for_gate`，展示字段 `relative_difference_pct = round(float(difference_for_gate), 2)`。`difference_for_gate <= Decimal("2.0")`（含恰好2%）为 compatible，`>2.0` 为不兼容；测试必须包含 PB 3.00 对 2.94 的对抗性恰好2%边界。
- 最新报告 BPS、报告期、当前 PB、年报 BPS、quote source/as-of 或 snapshot source/announcement 任一缺失、非正、非有限或格式无效：`status=incomplete`、`timing_eligible=false`、`reason_code=missing_or_invalid_input`；不得伪装 compatible。
- `difference_for_gate <= 2.0`：`status=compatible`、`timing_eligible=true`、`reason_code=within_2pct`，不因报告期标签相同而绕过数值门禁。
- 报告期不同且 `difference_for_gate > 2.0`：`status=period_mismatch`、`timing_eligible=false`、`reason_code=different_period_value_mismatch`。
- 报告期相同但 `difference_for_gate > 2.0`：`status=incomplete`、`timing_eligible=false`、`reason_code=same_period_value_mismatch`。
- 该字段只控制 timing eligibility；基本面 `scoring_status` 仍由评分输入和 latest-report 基本面冲突门控制。
- 由 `fetcher.py` 一个纯 helper 在 `_fetch_pb_pe_data` 后构造一次并写入 fundamentals JSON；不在 `store.py` 或 cache read path 重算/回填。outer `field_provenance.source=computed`；nested quote source/as-of 来自已校验 quote，latest BPS source/announcement 来自 `latest_report_snapshot`。

## 验收标准

1. QA/Research 静态 contract tests 先 RED：pin 合法 `scoring_status=incomplete`、timing-only incomplete、无理由漏评级三种合同，以及 report-contract 中的 `not_formed` 模块。独立 host-level QA smoke 记录三种报告预期 verdict；不新增本地 QA evaluator/CLI，也不把文本契约测试声称为确定性 verdict 执行器。
2. Research contract test 先 RED：`FUNDAMENTALS_HIT` 固定数据卡字段与 exact snapshot paths 完整，明确区分有值未展示、top-level missing 与 nested status missing。
3. Fetcher tests 先 RED 后 GREEN：覆盖 different-period mismatch、same-period >2%、compatible、missing/invalid，并断言恰好2%和最近选定的>2%反例、公式、报告期、reason_code、provenance 和 `timing_eligible`。
4. cache readback fixture 包含 `valuation_compatibility`，无需数据库迁移。历史 JSON 不含新字段时仍可读取且保持 absent；Research 消费时必须按 `reason_code=legacy_field_absent` 视为 timing incomplete/not eligible，不得 read-time 回填或写回。
5. `bash scripts/check.sh`、`git diff --check` 通过。
6. 对冻结实际 diff 执行一次独立只读审查（AGY 可用时优先；其 headless 权限阻塞时使用已授权 fallback reviewer）；父级核验所有 blocker/important。
7. 源仓库提交与生产 cutover 分离；生产安装前另行确认。切换后先成功执行公共 `a-stock-fetch fetch 002594`，再由 `a-stock-cache check 002594` JSON 回读新字段；fetch 命令本身不新增 JSON 输出。数据库 schema/user_version、配置与 cron 指纹不变。

## 回滚与停止条件

- 每个实现 commit 可单独 revert。
- QA 变化若允许无理由漏评级、runtime 变化若写入新 DB schema、改变原有 PB/PE/PS 字段或评分/动作语义，立即停止。
- 候选 runtime 仅在隔离 fixture 与临时环境验证；未获生产 cutover 单独批准前，不安装、不改 active client symlink、不改公共命令。
