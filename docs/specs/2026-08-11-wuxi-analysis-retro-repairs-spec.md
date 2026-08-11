# 药明康德投研复盘缺陷修复规范（2026-08-11）

## 背景

603259 首次研究暴露出六个可复现缺陷：A 框架缺少结构化近 5 年 PE 分位；缓存字段 `pe_ttm` 实为静态 PE；Research 的 fetch/check 顺序容易被并行误读；Skill 引用文件虽存在但未被 `skill_view` 显式发现；QA 将 Important FAIL 汇总成 PARTIAL，且把缺少完整报告的无效运行误报为 NON_COMPLIANT；A 框架满分无法表达经正式披露确认的重大跨境/客户集中风险。

## 目标

在不增加依赖、不改数据库 schema、不写生产缓存/持仓/账本、不部署 active Skill 的前提下，修复 canonical 项目中的数据与 Skill 契约，使相同案例 fail-closed、可测试、可复算。

## 范围

1. Runtime fetcher
   - 新增 `pe_static`，定义为当前已验证价格除以最近完整年报 EPS。
   - 暂时保留 `pe_ttm` 兼容别名，值与 `pe_static` 相同并明确 deprecated；不得把别名解释为真实 TTM。
   - 新增同口径 `pe_percentile_5y`；复用一次 10 年价格抓取，但计算函数必须按 `years` 裁剪预载价格窗口，避免 5 年调用实际使用 10 年样本。
   - 为新增字段写入 provenance；10 年字段保持兼容。
2. Research Skill
   - 将前置命令写成不可并行的串行流程：`a-stock-fetch fetch` 成功后再 `a-stock-cache check`；批量流程同样遵守。
   - FUNDAMENTALS_HIT 字段表优先称 `pe_static`，说明 `pe_ttm` 仅为兼容别名；A/E/F 可直接使用结构化 5 年 PE 分位，但仍需核验报告期与口径。
   - 显式链接 A—F、step8 和 catalyst references，保证宿主可发现 linked files。
   - A 框架增加不改 60 分结构的外部集中风险覆盖标签：`外部集中风险[状态=正常|受限|重大;...]`。正式披露确认重大跨境限制且单一地区/客户集中时，配置分/级仍展示，但必须标“置信度受限”，动作不得因 60/60 自动升级；最终动作仍服从既有矩阵及治理约束。
3. QA Skill / rubric
   - 输入缺少完整报告正文、只有摘要/修订说明、路径不可读或工具异常时返回 `verdict: INVALID_RUN`，不得返回 NON_COMPLIANT，也不进入合规分母。
   - Verdict 汇总为硬规则：任一 Critical/Important FAIL → NON_COMPLIANT；仅 Minor FAIL → PARTIAL；无 FAIL → COMPLIANT。
   - rubric 外建议只能放 `Advisory`，不得影响 verdict。
   - 显式链接 research rubric；rubric 增加外部集中风险覆盖检查，并确认近 5 年结构化字段仍受时点/口径门约束。
4. Tests and current normative docs
   - 增加聚焦 fetcher、Research/QA contract、reference discovery regression。
   - 更新 README/CHANGELOG 中会因新字段或 QA verdict 变化而失真的当前说明；不改历史审查记录。

## 非范围

- 不实现真实 TTM 利润平台、PS/PEG、融资融券结构化 provider、自动除息预检、回测或自动交易。
- 不移除 `pe_ttm`，不迁移数据库，不改现有缓存记录。
- 不修改 active `~/.hermes/skills/**`、cron、凭证、运行时安装或生产数据。
- 不改变 A 框架 60 分权重或创建新的数值扣分阈值。

## 不变量

- 所有当前价衍生字段必须携带行情时点 provenance。
- 5 年分位缺失、过期或口径不兼容时仍 `incomplete`，不得用 10 年分位替代。
- QA 文本合规 PASS 不证明外部事实或投资有效性。
- W1 写入继续要求 `--confirm-write`。

## 验收标准

1. 给定 10 年预载价格，`compute_pe_percentile(..., years=5)`只使用末端 5 年样本；测试能区分错误的 10 年结果。
2. fetch payload 同时含 `pe_static`、兼容 `pe_ttm` 和 `pe_percentile_5y`，值及 provenance 正确。
3. Research contract 测试固定串行顺序、禁止并行、5 年字段、兼容别名和显式 reference links。
4. QA contract 测试固定 `INVALID_RUN`、Important/Critical 汇总、Advisory 不影响 verdict，并能发现 rubric 链接。
5. A 框架和 QA rubric 同时包含外部集中风险标签及置信度受限语义，不产生第二动作出口。
6. `uv run pytest -q`、`uv run ruff check .`、`uv run python scripts/validate.py`、`python3 -I tests/qa/standalone_smoke.py`、`git diff --check`通过。

## 回滚与停止条件

- 基线：`a92990f`。
- 仅恢复本规范修改文件；不执行 reset/rebase，不触碰生产状态。
- 若新增字段破坏旧缓存读取、5 年窗口无法以现有数据正确计算、QA standalone 失去独立性或完整测试出现无法在本范围内修复的回归，则停止，不部署、不提交。
