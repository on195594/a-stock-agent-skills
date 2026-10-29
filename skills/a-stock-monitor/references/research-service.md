# Research 服务：先复用，再补证据

通过 `a-stock-cache research` 使用 `research-v1`。凭据仅由 CLI 从环境变量或所选私有配置读取，不进入提示词、日志或命令参数。未配置时说明不可用，继续原有已授权公开取证；服务错误必须保留，不把失败当作没有报告。

HTTP 401 时停止重试，交由 owner 修复凭据及环境覆盖；恢复后沿用原 request-id。日常研究不签发或轮换 Key，不取得网页登录或账户写权限；配置和轮换由项目运维文档维护。

1. 先运行 `a-stock-cache research reports <六位代码>`，再按问题读取相关的 `research report <报告ID> --compact`。需核对关键原文或程序财务表时，才读取同一报告的完整 `research report <报告ID>`；精简视图不等于引文已核验。已在会话提供完整报告与证据时直接复用，不重复查询。
2. 检查 `status`、`passed`、`question`、`coverage.periods/missing/limits`、`evidence.market_date` 和各来源披露/取得时间。`created_at` 不是证据日期，历史结果不自动更新。同时核对 `continuation` 的财报期、生成时间、行情日期与公告检索截止日；`historical_not_live_checked` 不是“最新”。先看 `continuation.baseline_status`：非 `ready` 时，空的 `previous_checkpoints` 不代表没有旧检查点，须解释基线缺失、失败、未就绪或冲突；只有可用基线才进行旧疑点对照。`previous_checkpoints` 仅为待核查问题，`table_changes` 仅为同口径数据变化，不等于投资理由改变。失败报告先解释 `diagnostics.problems/gaps/next_step`，只用已复核 `facts` 并保留 `problems`，不把预算提示当作已确定的失败根因，不自动付费重跑。
3. 有 `checkpoints` 时，复用其中的下期观察条件并核对本期证据，不把观察条件当作已发生事实；旧报告缺此字段不补造。主动研究同公司且未指定父报告时，服务会按自身规则接续最近合格报告的风险与检查点，Skill 不另建历史摘要或接续状态。已有证据足够就回答；新披露、冲突或关键缺口才发起任务。新任务前用 `research budget` 读取调用上限；这是循环保护而非金额预算，费用未知不得写成免费。用户有硬金额上限而服务无法保证时停止澄清。把最值得补的一项问题写清楚：
   ```bash
   a-stock-cache research start <代码> --question '<待解决的问题>' --request-id '<本次唯一编号>'
   # 追问已有报告时再加 --parent-report-id <报告ID>
   a-stock-cache research status <任务ID>
   a-stock-cache research report <返回的report_id> --compact
   ```
   提交只返回任务号。后续读取状态时等待合理间隔（例如 30 秒），避免密集轮询；本轮执行窗口结束仍未完成就交代任务号，后续接着查同一任务。提交超时先用 `a-stock-cache research resume --request-id <原编号>` 只读找回任务，不重提、不恢复执行失败任务。404 也不证明原提交失败；不换编号重建，必要的原样重试须沿用同一 request-id。改问题另需确认新任务与成本。服务尚不支持新读取接口时明确兼容性缺口，不因此重开研究。
4. 发现具体错误时：`a-stock-cache research feedback <报告ID> --location 'risks[0]' --text '<可核查的纠错说明>' --request-id '<唯一编号>'`。位置用报告实际 `summary` 或 `answer/risks/business/financial/methods/checkpoints` 数组下标。反馈产生关联的新报告，不覆盖旧文；先查新结果，不能把反馈本身当成已验证结论。`methods` 是带出处和适用边界的方法线索，跨公司使用仍需核查；针对 `methods[i]` 的成功核查会替换该条历史方法，空列表可撤下失效方法，失败不生效。
5. 回答保留报告 ID、源文档页码/引文或表格期间，说明哪些旧判断仍成立、哪些被新证据推翻、尚缺什么以及下一项取证的时间或触发条件。没有可比基线或没有增量就明确说明，不另建持仓状态、不自动更新 L3。不把旧报告当成原始证据，不因 `passed=true` 宣称投资结论正确。

研究方法、提示词和 A—F 框架均可提出反证或替代假设；公开证据问题不以完成评分为前提。服务不授予投资政策变更、交易或 W1 权限，也不替代 decision-v1/monitor-v1。完整首次配置研究仍按原评分和 QA 合同；服务报告不冒充该机器状态，且不提交给只支持 Skill 文本 rubric 的 QA。
