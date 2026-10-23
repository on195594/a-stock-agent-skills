# Research 服务：先复用，再补证据

服务使用 `research-v1`，通过 `a-stock-cache research` 调用。URL 和短期 Agent 令牌通过环境变量或所选的 0600 `runtime.env` 提供：`A_STOCK_RESEARCH_URL`、`A_STOCK_RESEARCH_TOKEN`。不读取其他项目 `.env`；令牌由 Research owner 签发，配置与使用沿用当前任务授权。未配置时说明不可用，继续原有已授权公开取证；服务错误必须保留，不把失败当作没有报告。

1. 先运行 `a-stock-cache research reports <六位代码>`，再按问题读取相关的 `research report <报告ID>`。已在会话提供完整报告与证据时直接复用，不重复查询。
2. 检查 `status`、`passed`、`question`、`coverage.periods/missing/limits`、`evidence.market_date` 和各来源披露/取得时间。`created_at` 不是证据日期，历史结果不自动更新。失败报告只用 `facts` 并保留 `problems`。
3. 已有证据足够就回答；新披露、冲突或关键缺口才发起任务。把最值得补的一项问题写清楚：
   ```bash
   a-stock-cache research start <代码> --question '<待解决的问题>' --request-id '<本次唯一编号>'
   # 追问已有报告时再加 --parent-report-id <报告ID>
   a-stock-cache research status <任务ID>
   a-stock-cache research report <返回的report_id>
   ```
   提交只返回任务号。后续读取状态时等待合理间隔（例如 30 秒），避免密集轮询；本轮执行窗口结束仍未完成就交代任务号，后续接着查同一任务。网络失败后原样重试必须沿用同一 request-id；改问题才换编号。
4. 发现具体错误时：`a-stock-cache research feedback <报告ID> --location 'risks[0]' --text '<可核查的纠错说明>' --request-id '<唯一编号>'`。位置用报告实际 `summary` 或 `answer/risks/business/financial/methods` 数组下标。反馈产生关联的新报告，不覆盖旧文；先查新结果，不能把反馈本身当成已验证结论。`methods` 是带出处和适用边界的方法线索，跨公司使用仍需核查；针对 `methods[i]` 的成功核查会替换该条历史方法，空列表可撤下失效方法，失败不生效。
5. 回答保留报告 ID、源文档页码/引文或表格期间，说明哪些旧判断仍成立、哪些被新证据推翻、尚缺什么以及下一项取证。不把旧报告当成原始证据，不因 `passed=true` 宣称投资结论正确。

研究方法、提示词和 A—F 框架均可提出反证或替代假设；公开证据问题不以完成评分为前提。服务不授予投资政策变更、交易或 W1 权限，也不替代 decision-v1/monitor-v1。完整首次配置研究仍按原评分和 QA 合同；服务报告不冒充该机器状态，且不提交给只支持 Skill 文本 rubric 的 QA。
