# 工程契约与安全边界审查报告

**审查对象**：`/home/lin/a-stock-agent-skills` 纯工程修复快照  
**审查模式**：严格只读 / 无工具调用 / 独立审查  

---

## 1. 授权与边界评估 (Authorization & Scope Assessment)

- **授权判断**：**未越界（符合授权）**。
- **依据**：
  1. 本批改动未包含任何投资规则变更（评分公式、止损阈值、框架参数、仓位建议、Tier 语义均未触碰）。
  2. `SCHEMA_MIGRATIONS` 迁移定义 tuple 列表未作任何增删改，仅重构了执行迁移的 helper 函数签名与调用链路。
  3. 未触碰生产 SQLite 数据库、生产 Cron 任务、外部凭证或 active client symlink 映射。
  4. 属于授权范围内的纯工程与测试基建修复。

---

## 2. 输出合同 (Output Contract)

### Verdict
`PASS_WITH_NOTES`

---

### Blocking findings
无

---

### Important notes

1. **`test_help_states_the_write_gate_and_lists_every_w1_command` 单向断言优化**  
   新增测试断言“所有真实 W1 命令都出现在 `--help` 的 W1 段落中”，但未校验反向（即“被列入 W1 段落的名字必须确实是 W1”）。虽然这不会导致安全门禁失效，但若将来误将 R0 命令手写进 W1 段落，测试仍会通过。建议后续补充反向校验。
2. **零参 W1 命令 `cleanup` 的多余参数防御**  
   重构后 `cmd_cleanup(args)` 保持了与原 `_invoke` 相同的“静默忽略多余参数”行为。虽然行为严格等价且仅清理已过期缓存（不触碰持仓账本），但从防御性编程角度看，未来可考虑在 `cmd_cleanup` 内对 `args` 做 `if args: ...` 校验，避免用户误敲 `cleanup 600519` 时产生“只删了 600519”的误解。

---

### Engineering semantics (工程语义判断)

1. **Schema 迁移重构与事务原子性**
   - **完全保留原闭包语义**：是的。原 `_bootstrap_database_schema` 内部闭包 `apply_column_migration` 即在无 `conn.commit()` 的情况下执行 `conn.execute(sql)`。新提升的模块级 `apply_column_migration(conn, sql)` 逻辑与其 100% 一致。
   - **严格变好**：删除了原先存在于 `apply_schema_migrations`（仅测试引用）中的逐条 `conn.commit()`，将 DDL 执行统一归口至 `schema_ledger.bootstrap_schema` 的整体事务控制下。若中途某条 DDL 失败，整批修改将统一回滚，避免了“DDL 已提交但 ledger 记录未写入”的不一致风险。
   - **反向风险判断**：在 SQLite 中，DDL 语句（如 `ALTER TABLE ADD COLUMN`）支持完整事务回滚（Transactional DDL）。因此在 SQLite 环境下不存在“隐式提交导致回滚失效”的反向风险。

2. **删除 public 名字 `apply_schema_migrations` 的 API 契约**
   - **不构成破坏**：`a_stock_agent_runtime` 是随 installer 整体打包部署的内部 runtime 模块，并非发布在 PyPI 上的第三方公共 Python 库。仓库内 `grep -rn` 已确认全量代码与测试无外部依赖该函数；变更已在 `CHANGELOG.md` 中记录。

3. **删除 `_invoke` 与 5 个零参命令签名重构**
   - **行为严格不变**：原 `_invoke` 分支对这 5 个命令也是直接调用零参 `COMMANDS[command]()`，同样会丢弃传入的 `remaining` 参数。重构为 `COMMANDS[command](remaining)` 并将函数签名统一为 `args: list[str] | None = None` 后，行为完全等价。
   - **风险与 `cleanup` 升级评估**：该“静默忽略”是既有行为继承，非本次重构引入的回归；`cleanup` 仅用于删除已被 TTL 标记为过期的基本面/分析缓存，不影响持仓或交易账本，且处于全局 `--confirm-write` 保护之下，因此**不应升级为 blocker**。

4. **`--help` W1 清单单向断言漏洞分析**
   - **不构成 blocker/安全漏洞**：该测试的核心防护目标是**防止新增/修改 W1 命令时忘记在 `--help` 中声明写入门禁**。若误将 R0 命令写进 W1 清单，运行时 `COMMAND_CLASSIFICATION['holdings']` 仍为 `R0`，`main()` 依然允许无 `--confirm-write` 执行，不会阻塞只读操作或破坏安全门禁。

5. **安装测试改为 `skip` 的影响**
   - **属于净改善**：原测试硬编码 `/home/lin/a-stock-lib` 路径，在缺失依赖的环境下会直接报错 `FileNotFoundError`；改用 `A_STOCK_LIB_SOURCE` 环境变量 + 条件 `skip` 后，既支持自定义路径，又保证了在未 provision `a-stock-lib` 的裸 CI/开发机上输出清晰的 `skipped` 原因（`a-stock-lib not provisioned...`）。在已 provision 环境中，5 项测试全量执行并通过（`5 passed in 8.19s`）。

6. **`UV_CACHE_DIR` 隔离性评估**
   - **不自相矛盾，设计合理**：测试通过重定向 `HOME` 隔离的是安装目标路径（`.agents` / `.claude` / `.local` 等配置与脚本），而 `UV_CACHE_DIR` 是只读的 Python wheel/build-system cache。在 `UV_OFFLINE=1` 约束下共享宿主机 `uv` 缓存，既保证了离线环境构建 `uv build` 所需依赖（如 `setuptools`）可被找到，又没有破坏测试对目标文件系统的写隔离。

7. **`uv sync --frozen --inexact` 的依赖管理立场**
   - **正确尊重既有设计**：`a-stock-lib` 是由 installer 显式传入并记录 SHA256 来源凭据的本地外置核心库，故意不在 `pyproject.toml` 的 PyPI 依赖列表中声明。默认 `uv sync --frozen` 会强制卸载任何未在 `uv.lock` 中的包（导致 `a-stock-lib` 被卸载）；使用 `--inexact` 是 `uv` 官方推荐的保留外置已安装包的标准用法。

---

### Test assessment (测试评估)

1. `tests/research/test_cache.py` -> `test_schema_migration_ignores_only_duplicate_column`:
   - 正确适配了 `cache.apply_column_migration(conn, sql)` 的新签名，精准验证了“遇到 duplicate column 忽略，遇到 locked 等其他 OperationalError 正常 raise”的边界契约。
2. `tests/test_command_classification.py` -> `test_help_*`:
   - `test_help_documents_every_command`: 确保 `COMMANDS` 中所有子命令均在 docstring 中有文档说明。
   - `test_help_states_the_write_gate_and_lists_every_w1_command`: 确保 `--confirm-write` 说明与所有 W1 命令无一遗漏地写在 `--help` 的门禁段落中。
3. `tests/test_installation.py`:
   - 引入 `UV_CACHE_DIR` 解决了子进程 `uv build` 在隔离 `HOME` 下丢缓存的硬伤；通过 `A_STOCK_LIB_SOURCE` 动态定位替代硬编码路径，契约覆盖完整。

---

### Recommended next step (恰好一个动作)

直接合并并提交本批工程修复（`git commit`），无需进一步修改。
