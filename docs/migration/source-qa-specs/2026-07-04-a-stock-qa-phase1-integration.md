# Phase 1 集成设计规格

> 范围：a-stock-qa × a-stock-research，手动验证阶段
> 目标：在不修改 a-stock-research SKILL.md 的前提下，验证 rubric 质量，积累校准案例

---

## 阶段目标

Phase 1 不做自动集成，原因：
- rubric 9 项检查是初稿，粒度和措辞需要在真实输出上验证
- 过早自动化会让每次分析都承担未经校准的 QA 噪音

Phase 1 结束条件：**5 次以上手动 QA 运行，误报率（FAIL 但实际 PASS）< 20%**。

---

## 手动调用流程

### 步骤

1. 正常运行 `/a-stock-research <代码>` 完成分析
2. 分析完成后，手动调用：
   ```
   /a-stock-qa
   skill_type: a-stock-research
   output: <将完整分析报告文本粘贴至此>
   ```
3. a-stock-qa 输出结构化 verdict（见下方格式）
4. PM 人工核查每个 FAIL 项是否为真实问题

### 调用时机

- **推荐**：每次运行 a-stock-research 后都跑一次（积累数据快）
- **最低要求**：每周至少 2 次，覆盖不同行业框架（A/B/C/D/E/F 各至少 1 次）

---

## Verdict 输出格式（示例）

```markdown
## a-stock-qa 合规检查报告

**Skill type**: a-stock-research
**股票**: 601288 农业银行
**检查时间**: 2026-07-05
**整体 verdict**: PARTIAL

### 检查明细

| # | 检查项 | 级别 | 结果 | 说明 |
|---|--------|------|------|------|
| 1 | fetcher 先行 | Critical | PASS | 报告标注"从缓存读取实时价格" |
| 2 | 框架路由正确 | Important | PASS | 银行股→B框架，路由正确 |
| 3 | 格雷厄姆数 | Important | SKIP | 报告注明"金融股，改用 PB<1.0 判断" |
| 4 | 异动检测 | Important | PASS | 第零步结果"无异常涨停，无减持公告" |
| 5 | data_period 标注 | Important | PASS | ROE/NIM 均有"2025年报"标注 |
| 6 | checklist 核验 | Important | SKIP | B框架不需要 checklist |
| 7 | 股息率交叉验证 | Important | SKIP | FUNDAMENTALS_HIT 路径豁免 |
| 8 | 关键字段缺失警告 | Minor | FAIL | PE分位 null 但报告无 ⚠️ 提示 |
| 9 | 双轨评级完整 | Important | PASS | 配置评级 B级 + 时机评级 ★★ 均存在 |

### 结论

存在 1 项 Minor 问题（检查 #8）：PE分位字段为 null 但未显示前置警告。
不影响分析结论可用性，建议下次修正。
```

---

## 误报处理规则

PM 核查后，如果某个 FAIL 判断是误报（QA 判错了）：

1. 记录误报原因：PASS 信号文本不够明确 / rubric 判断逻辑有歧义
2. 更新 `rubrics/a-stock-research.md` 对应检查项的 PASS 信号描述
3. 如果同类误报出现 ≥2 次，创建校准案例文件：
   ```
   rubrics/calibration-cases/<task-id>-<date>.md
   ```
   格式参考 `~/.claude/skills/ai-collab/_shared/references/qa-calibration-cases/README.md`

---

## Phase 1 → Phase 2 升级条件

满足以下全部条件后，进入 Phase 2（自动集成到 a-stock-research）：

- [ ] 手动运行 ≥5 次（覆盖 ≥3 种框架）
- [ ] 误报率 < 20%（FAIL 中 < 1/5 是误报）
- [ ] 无 Critical 级检查项出现过漏报（研究发现 Critical 问题但 QA 未报 FAIL）
- [ ] rubric 版本 ≥ v1.1（有过至少一次基于真实误报的修订，而非仅有初稿）

---

## Phase 2 预设集成方案（仅供参考，执行时再确认）

a-stock-research SKILL.md 末尾（第六步之后）新增：

```markdown
## 第七步：质量合规检查（自动）

分析报告输出完成后，dispatch a-stock-qa 独立检查：

dispatch Agent() with:
  skill_type: a-stock-research
  output: <完整报告文本>

- COMPLIANT → 在报告末尾附注"✓ a-stock-qa 合规检查通过"
- PARTIAL → 在报告末尾附注"⚠️ a-stock-qa 发现 Minor 问题：[列表]"
- NON_COMPLIANT → 在报告**首部**置顶警告"⛔ a-stock-qa：以下步骤存在合规问题，报告可信度降低：[列表]"
```

---

## 风险与局限

1. **文本解析局限**：a-stock-qa 基于报告文本判断，无法验证数据源头准确性
   （如 fetcher 返回的 EPS 数值是否正确不在检查范围内）
2. **判断主观性**：部分检查项（如"异动检测已执行"）依赖文本措辞，
   分析风格变化可能导致误报率波动
3. **新框架兼容性**：未来如 a-stock-research 新增框架类型，需同步更新 rubric
