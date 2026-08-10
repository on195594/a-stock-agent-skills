你是独立的工程契约与安全边界审查员，审查 `/home/lin/a-stock-agent-skills`（A股投研 Skill 套件 canonical 仓库）的一批**纯工程修复**。只审查下面的快照，不访问或修改任何文件，不调用工具，不执行命令。审查必须严格、只读。

该仓库通过 symlink 同时驱动 Claude / Codex / Hermes 三个客户端的 active Skill，`a-stock-cache` CLI 直接读写用户真实持仓账本（SQLite）。因此**任何削弱 W1 写入门禁、schema 迁移原子性或 fail-closed 语义的改动都是 blocker**。

## 输出合同

- `Verdict`: `PASS` / `PASS_WITH_NOTES` / `REQUEST_CHANGES`
- `Blocking findings`: 每项给出快照证据、风险、最小修复；没有写“无”
- `Important notes`: 非阻塞项
- `Engineering semantics`: 明确判断以下七点
  1. 删除 `apply_schema_migrations` 后，`apply_column_migration` 提升为模块级并接受 `conn` 参数，是否**完全保留**了原 `_bootstrap_database_schema` 内闭包的语义？特别是：新函数不自行 `commit`，由 `schema_ledger.bootstrap_schema` 在整批迁移后统一 commit——这是否让"某条迁移失败"从"已 commit 的半截 schema"变成"整批回滚"，即严格变好？有没有反向风险（例如 sqlite DDL 隐式提交导致回滚并不生效，从而 ledger 与实际 schema 不一致）？
  2. 被删的 `apply_schema_migrations` 在删除前**只有测试引用**（已用 `grep -rn` 在 `src/ tests/ scripts/ skills/` 全量确认）。但它是 public 名字（无下划线前缀），已发布的 `v0.1.0` wheel 已部署到生产 runtime。删除它是否构成对外 API 破坏？考虑到 installer 是整包替换、且无第三方消费者，这个判断是否成立？
  3. 删除 `_invoke` 后，5 个原零参命令（`holdings` / `check-holdings` / `list` / `cleanup` / `retro-pending`）签名改为 `args: list[str] | None = None`，由 `main` 统一传入 `remaining`。**行为是否严格不变**？注意：这 5 个命令现在会静默忽略多余参数——但在删除前 `_invoke` 也是丢弃 args 调用零参函数，同样静默忽略。这个"静默忽略"本身是否是风险？其中 `cleanup` 和 `clear` 属于 W1（`cleanup` 在这 5 个之内），用户误敲 `cleanup 600519` 期待"只清某只"却清了全部过期缓存，是否应该升级为 blocker 要求拒绝多余参数？（`cleanup` 只删过期缓存，不碰 holdings/交易账本。）
  4. `--help`（模块 docstring）新增的 W1 命令清单是**手写**的，与 `COMMAND_CLASSIFICATION` 的真实分级由新测试 `test_help_states_the_write_gate_and_lists_every_w1_command` 绑定：该测试只断言"每个 W1 命令名出现在 gate 段落"，**不断言反向**（gate 段落里出现的名字必须确实是 W1）。这个单向断言是否留下真实漏洞——例如把一个 R0 命令误写进 W1 清单，测试仍然通过，用户被误导以为只读命令需要 `--confirm-write`？
  5. 安装测试从"硬失败"改为"缺 a-stock-lib 时 skip"。skip 是否会掩盖真实回归（即在任何未 provision lib 的环境里，installer 永远无人验证）？相比原先"在唯一开发机上因 uv 缓存问题红着、且路径硬编码"，这是净改善还是把问题藏起来？
  6. 引入 `UV_CACHE_DIR`：测试换 `HOME` 隔离，却显式把宿主机 uv 缓存路径传回子进程。这是否与"测试隔离"目标自相矛盾？有没有更干净且不引入网络依赖的替代（例如不设 `UV_OFFLINE`、或预热一个 tmp 缓存）？
  7. `uv sync --frozen` → `--inexact`：`a-stock-lib` 被刻意排除在 lockfile 外（installer 用 `--a-stock-lib-source/--wheel` 显式提供并记录 provenance）。用 `--inexact` 保住它，是**正确尊重既有设计**，还是**掩盖了真正的依赖管理缺陷**（应当把 lib 纳入 lock 或用 `[tool.uv.sources]`）？请给出明确立场。
- `Test assessment`: 聚焦新增/改写的 3 个测试是否真的覆盖了它们声称的契约；不要要求新测试工程，也不要要求补全 `cache.py` 的整体覆盖率。
- `Recommended next step`: 恰好一个动作。

## 授权范围

用户明确授权对该仓库做上述工程修复并让 AGY 复审。仓库规则（`AGENTS.md`）要求：投资规则变更须有 dated spec + 聚焦回归 + 只读复审；数据库 schema、生产 cron、active client 条目须单独授权。

**本批改动明确不含任何投资规则变更**：不改评分、止损阈值、框架系数、L3/Tier 语义、仓位建议或任何交易动作。`SCHEMA_MIGRATIONS` 列表内容一字未改（只改了执行它的函数形态）。未新增/删除/修改任何迁移条目，未触碰生产数据库、cron、凭证、持仓或交易记录。

请据此判断本批是否**越界**（例如：是否实际上构成了 schema 变更而需要单独授权）。

## 已知的、审查前自陈的薄弱点

提交审查方（Claude）主动声明以下三点，请独立判断其严重性，不要因为已自陈就降级：

1. `--help` 的 W1 清单是手写冗余数据，理论上可与 `COMMAND_CLASSIFICATION` 漂移（见 Engineering semantics 第 4 点）。
2. `scripts/check.sh` 用 `set -euo pipefail` 且第一步是 `uv sync --frozen --inexact`；在无网络环境下该步是否会失败并阻断后续所有本地检查（`uv sync --frozen` 理论上应可离线完成，但未验证）。
3. 本仓库 `git remote -v` 为空、`a-stock-lib` 亦无远端且不在任何 package index 上，因此没有落地 GitHub Actions，改为本机 `scripts/check.sh`。请判断这是合理取舍还是回避。

## 请反驳提交方上一轮的两处误判

提交方在上一轮工程审查报告中犯过两个错，已自行更正，请确认更正本身是否正确、以及是否还有同类错误残留在本批改动里：

1. 曾把 `README.md` 的 “The `v0.1.0` runtime release is deployed” 报为版本漂移（因 `pyproject.toml` 是 `0.1.1`）。实际 `docs/CHANGELOG.md` 写明 “the next repository release is `0.1.1`”，即 0.1.1 未发布、0.1.0 才是部署版本，README 正确。提交方据此**未修改** README 的版本行。
2. 曾建议新增 `.github/workflows/ci.yml`，未先检查仓库是否有远端。

## 变更快照

以下为本批改动的完整 `git diff`（跟踪文件）与新增文件全文。工作区中还有两个与本批**无关**的既存改动（`skills/a-stock-research/SKILL.md` 的 catalyst-cycle 路由段落、`tests/research/test_p0_contracts.py` 的对应测试，以及两个未跟踪的 catalyst-cycle 文档），**不属于本次审查范围，未包含在下方快照中**。

### git diff（跟踪文件，已排除无关改动）

```diff
diff --git a/README.md b/README.md
index dccd4ce..9e2e3f1 100644
--- a/README.md
+++ b/README.md
@@ -75,8 +75,18 @@ credential, runtime log or Telegram token in the repository.
 
 ## Development checks
 
+Run every gate with one command:
+
+```bash
+bash scripts/check.sh
+```
+
+It runs the individual checks below. Use `--inexact` whenever syncing by hand:
+`a-stock-lib` is deliberately absent from the lockfile, so a plain
+`uv sync --frozen` uninstalls it and breaks every runtime import.
+
 ```bash
-uv sync --frozen
+uv sync --frozen --inexact
 uv run pytest -q
 uv run ruff check .
 uv run python scripts/validate.py
diff --git a/docs/CHANGELOG.md b/docs/CHANGELOG.md
index e736319..29b11e8 100644
--- a/docs/CHANGELOG.md
+++ b/docs/CHANGELOG.md
@@ -4,6 +4,15 @@
 
 ### Fixed
 
+- Development environment: documented `uv sync --frozen --inexact`; the plain form uninstalled the externally provisioned `a-stock-lib` and broke every runtime import.
+- Installer tests no longer depend on a warm host `uv` cache reachable through the relocated `HOME`, and locate `a-stock-lib` via `A_STOCK_LIB_SOURCE` instead of a hardcoded path, skipping when it is absent.
+- `a-stock-cache --help` now states the global `--confirm-write` gate and its W1 command list, and documents the four `retro-*` commands; a test keeps the text in sync with the command table.
+
+### Changed
+
+- Added `scripts/check.sh` as the single repository gate.
+- Removed the superseded `apply_schema_migrations` duplicate and the redundant `_invoke` dispatch branch; the migration ledger's `apply_column_migration` is now the only column-migration path.
+
 - Audit remediation (2026-08-09): R0 database access is physically read-only; unknown/stale quote timestamps cannot trigger stop-loss or portfolio-risk actions; installer releases are wheel-backed and preflighted with collision-free backups; migration and cron failures now fail closed.
 - Skill portability: research QA routing now uses host discovery without client-specific commands, QA scope matches its research-only rubric, and checklist output is client-neutral.
 - Maintenance: removed stale compatibility exports, broken legacy runners, and the unmaintained mypy gate; the next repository release is `0.1.1`.
diff --git a/docs/development.md b/docs/development.md
index d1abd1d..32a9d02 100644
--- a/docs/development.md
+++ b/docs/development.md
@@ -10,17 +10,24 @@ Requirements are Python 3.13+, `uv`, and an explicit `a-stock-lib` checkout or
 wheel. Install the locked development environment with:
 
 ```bash
-uv sync --frozen
+uv sync --frozen --inexact
 ```
 
+`--inexact` is required, not cosmetic. `a-stock-lib` is deliberately not a
+declared dependency — the installer takes an explicit checkout or wheel and
+records its provenance — so it is absent from the lockfile and a plain
+`uv sync --frozen` uninstalls it, breaking every runtime import.
+
 The source checkout is only needed when exercising the installer or the
 external prompt renderer. It must be passed explicitly; the project never
-guesses a sibling home-directory path.
+guesses a sibling home-directory path. Tests locate it at `~/a-stock-lib` or at
+`A_STOCK_LIB_SOURCE`, and skip when it is not provisioned.
 
 ## Validation matrix
 
 Run the smallest relevant check while iterating, then run the full matrix
-before committing:
+before committing. `scripts/check.sh` runs all of it in one command; this
+repository has no git remote, so that script is the only gate there is.
 
 ```bash
 uv run pytest -q
diff --git a/src/a_stock_agent_runtime/cache.py b/src/a_stock_agent_runtime/cache.py
index 952208e..f454fbc 100755
--- a/src/a_stock_agent_runtime/cache.py
+++ b/src/a_stock_agent_runtime/cache.py
@@ -2,6 +2,18 @@
 """
 A股投研数据缓存管理器
 用法：
+  cache.py [--confirm-write] <子命令> [参数...]
+
+写入安全边界（全局）：
+  --confirm-write 必须位于子命令之前。所有 W1（修改投资状态）子命令缺少该参数时
+  返回退出码 3，且不打开写事务；R0/R1 只读子命令不需要该参数。
+  W1：set / set-analysis / set-score / set-score-breakdown / set-flag / clear-flag /
+      alert-open / alert-pending / alert-resolve / l3-add / l3-update / tier-config /
+      tier-update / holding-framework / add-holding / buy-holding / sell-holding /
+      record-dividend / corporate-action / close-holding / retro-add / remove-holding /
+      update-return / cleanup / clear
+
+子命令：
   cache.py check <代码>                                  # 【推荐】一次性检查分析结论+基本面缓存状态
   cache.py get <代码>                                    # 获取基本面缓存数据
   cache.py set <代码> <名称> <行业> <JSON> [TTL]            # 写入基本面数据（TTL自动按行业推断）
@@ -27,6 +39,11 @@ A股投研数据缓存管理器
                                                         # 除权/送转，分离经济成本与规则参考成本
   cache.py close-holding <代码> <卖出价> [日期]           # 记录平仓（保留历史，用于评分验证）
   cache.py update-return <代码> <实际回报%>             # 卖出后记录实际回报（如 15.5 或 -8.2）
+  cache.py retro-add <代码> <error_tags> [--note 备注] [--thesis 买入理由] [--gap 框架改进建议]
+                                                        # 添加平仓复盘
+  cache.py retro-pending                                # 已平仓但尚未复盘的记录
+  cache.py retro-stats [框架名]                          # 复盘统计（按框架汇总错误标签）
+  cache.py retro-outliers [--loss N]                     # 亏损超阈值且未复盘的记录（默认 10）
   cache.py holdings                                     # 显示在仓持股 + 已平仓历史（含盈亏%）
   cache.py position-return <代码> [当前价]               # 交易事件口径总回报
   cache.py remove-holding <代码>                        # 彻底删除持仓记录（慎用）
@@ -225,17 +242,19 @@ def get_stop_loss_pct(framework: str) -> tuple[float, float]:
     return DEFAULT_STOP_LOSS_PCT
 
 
-def apply_schema_migrations(conn: sqlite3.Connection) -> None:
-    """Apply additive schema migrations, ignoring only duplicate-column cases."""
-    for _, col_def in SCHEMA_MIGRATIONS:
-        try:
-            conn.execute(col_def)
-            conn.commit()
-        except sqlite3.OperationalError as e:
-            if 'duplicate column name' in str(e).lower():
-                continue
-            logger.exception("Schema migration failed: %s", col_def)
-            raise
+def apply_column_migration(conn: sqlite3.Connection, sql: str) -> None:
+    """Add one column, ignoring only the already-applied duplicate-column case.
+
+    Committing is the migration ledger's job, so one failed item rolls the whole
+    batch back instead of leaving the ledger disagreeing with the schema.
+    """
+    try:
+        conn.execute(sql)
+    except sqlite3.OperationalError as exc:
+        if 'duplicate column name' in str(exc).lower():
+            return
+        logger.exception('Schema migration failed: %s', sql)
+        raise
 
 
 def _create_core_tables(conn: sqlite3.Connection) -> None:
@@ -606,17 +625,9 @@ def _bootstrap_database_schema(conn: sqlite3.Connection) -> None:
     ledger below is the cross-process guard: normal one-command CLI invocations
     must not rerun DDL, legacy backfills or migration probes on every startup.
     """
-    def apply_column_migration(sql: str) -> None:
-        try:
-            conn.execute(sql)
-        except sqlite3.OperationalError as exc:
-            if 'duplicate column name' not in str(exc).lower():
-                logger.exception('Schema migration failed: %s', sql)
-                raise
-
     migrations = [('001-core-tables', lambda: _create_core_tables(conn))]
     migrations.extend(
-        (migration_id, lambda sql=sql: apply_column_migration(sql))
+        (migration_id, lambda sql=sql: apply_column_migration(conn, sql))
         for migration_id, sql in SCHEMA_MIGRATIONS
     )
     migrations.extend([
@@ -1787,7 +1798,7 @@ def _print_closed_holdings(
             print(f"\n  已平仓统计：无可核验事件账本（共 {len(closed_rows)} 笔）")
 
 
-def cmd_holdings() -> None:
+def cmd_holdings(args: list[str] | None = None) -> None:
     """显示持仓列表：在仓持股 + 已平仓历史（含盈亏%，用于验证评分准确性）"""
     with db_session() as conn:
         # Lazy compatibility migration for legacy rows imported after process
@@ -2308,7 +2319,7 @@ def cmd_retro_add(args: list[str]) -> None:
     print(f"复盘已记录：{code} | 标签:{error_tags} | 实际回报:{actual_return_pct:+.1f}%{inferred_note}")
 
 
-def cmd_retro_pending() -> None:
+def cmd_retro_pending(args: list[str] | None = None) -> None:
     """显示已平仓但尚未复盘的记录。用法：retro-pending"""
     with db_session() as conn:
         _backfill_holding_metadata(conn)
@@ -2767,7 +2778,7 @@ def _evaluate_holding_status(
     return label, status, is_alert
 
 
-def cmd_check_holdings() -> None:
+def cmd_check_holdings(args: list[str] | None = None) -> None:
     """持仓止损检查：对比当前价与15%/20%止损线，主动预警（P3-4）。
     区分盘中现价/收盘价/上一交易日陈旧行情三种口径，非交易时段拿到隔夜收盘价
     时只输出观察提醒、不触发同等级止损预警（见 PITFALLS.md [BUG-006]）。
@@ -3447,7 +3458,7 @@ def cmd_watchlist(args: list[str] | None = None) -> None:
             print(_format_breakdown_line(row['score_breakdown']))
 
 
-def cmd_list() -> None:
+def cmd_list(args: list[str] | None = None) -> None:
     """列出所有缓存内容（含过期）"""
     today = cst_today()
     with db_session() as conn:
@@ -3486,7 +3497,7 @@ def cmd_list() -> None:
         print(f"  {display_name}({code}) [{status}]{score_str}{breakdown_str}{flag_icons} 创建:{format_timestamp_cst(created_at)}")
 
 
-def cmd_cleanup() -> None:
+def cmd_cleanup(args: list[str] | None = None) -> None:
     """清除所有过期的缓存条目"""
     with db_session() as conn:
         stocks = conn.execute(
@@ -3695,15 +3706,6 @@ COMMAND_CLASSIFICATION = {
 }
 
 
-def _invoke(command: str, args: list[str]) -> None:
-    if command in ('watchlist', 'portfolio-risk'):
-        COMMANDS[command](args)
-    elif command in ('list', 'cleanup', 'holdings', 'check-holdings', 'retro-pending'):
-        COMMANDS[command]()
-    else:
-        COMMANDS[command](args)
-
-
 def main(argv: list[str] | None = None) -> int:
     global _READ_ONLY_REQUEST
     args = list(sys.argv[1:] if argv is None else argv)
@@ -3738,7 +3740,7 @@ def main(argv: list[str] | None = None) -> int:
     print(f'[a-stock-cache] 操作数据库: {DB_PATH}', file=sys.stderr)
     try:
         _READ_ONLY_REQUEST = classification == 'R0'
-        _invoke(command, remaining)
+        COMMANDS[command](remaining)
     except SystemExit as exc:
         return int(exc.code or 0)
     except sqlite3.Error as exc:
diff --git a/tests/research/test_cache.py b/tests/research/test_cache.py
index 1827d1e..0f74735 100644
--- a/tests/research/test_cache.py
+++ b/tests/research/test_cache.py
@@ -785,9 +785,9 @@ def test_schema_migration_ignores_only_duplicate_column():
             raise sqlite3.OperationalError("duplicate column name: name")
 
         def commit(self):
-            raise AssertionError("commit should not run for duplicate-column errors")
+            raise AssertionError("the migration ledger owns commits, not this helper")
 
-    cache.apply_schema_migrations(DuplicateColumnConn())
+    cache.apply_column_migration(DuplicateColumnConn(), cache.SCHEMA_MIGRATIONS[0][1])
 
     class LockedConn:
         def execute(self, _sql):
@@ -797,7 +797,7 @@ def test_schema_migration_ignores_only_duplicate_column():
             raise AssertionError("commit should not run after failed execute")
 
     with pytest.raises(sqlite3.OperationalError, match="database is locked"):
-        cache.apply_schema_migrations(LockedConn())
+        cache.apply_column_migration(LockedConn(), cache.SCHEMA_MIGRATIONS[0][1])
 
 
 # ── update-return ──────────────────────────────────────────────────────────────
diff --git a/tests/test_command_classification.py b/tests/test_command_classification.py
index 8416859..53abfe3 100644
--- a/tests/test_command_classification.py
+++ b/tests/test_command_classification.py
@@ -1,3 +1,4 @@
+from a_stock_agent_runtime import cache
 from a_stock_agent_runtime.cache import COMMANDS, COMMAND_CLASSIFICATION
 
 
@@ -5,3 +6,17 @@ def test_every_cache_command_has_one_classification() -> None:
     assert set(COMMANDS) == set(COMMAND_CLASSIFICATION)
     assert set(COMMAND_CLASSIFICATION.values()) <= {"R0", "R1", "W1"}
     assert all(list(COMMAND_CLASSIFICATION.values()).count(name) >= 1 for name in ("R0", "R1", "W1"))
+
+
+def test_help_documents_every_command() -> None:
+    """`--help` prints this docstring, so it must not drift from the command table."""
+    assert cache.__doc__
+    assert [name for name in COMMANDS if name not in cache.__doc__] == []
+
+
+def test_help_states_the_write_gate_and_lists_every_w1_command() -> None:
+    """The confirmation gate is the only write protection; help must not omit it."""
+    gate_section, _, _ = cache.__doc__.partition("子命令：")
+    assert "--confirm-write" in gate_section
+    w1 = [name for name, level in COMMAND_CLASSIFICATION.items() if level == "W1"]
+    assert [name for name in w1 if name not in gate_section] == []
diff --git a/tests/test_installation.py b/tests/test_installation.py
index 9759a83..5c77999 100644
--- a/tests/test_installation.py
+++ b/tests/test_installation.py
@@ -7,10 +7,32 @@ import subprocess
 import sys
 from pathlib import Path
 
+import pytest
+
 from a_stock_agent_runtime.install import _backup
 
 
-def _run(args, home, path):
+# Resolved against the real environment at import time, before any test swaps HOME.
+# The installer shells out to `uv build`, which needs its package cache to satisfy
+# `build-system.requires` while UV_OFFLINE is set; a relocated HOME would hide it.
+UV_CACHE_DIR = os.environ.get("UV_CACHE_DIR") or str(
+    Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "uv"
+)
+
+# a-stock-lib is deliberately not a declared dependency: the installer takes an
+# explicit checkout or wheel and records its provenance.  Tests locate it the same
+# way an operator would, and skip rather than fail when it is not provisioned here.
+LIB_ROOT = Path(os.environ.get("A_STOCK_LIB_SOURCE") or Path.home() / "a-stock-lib")
+LIB_WHEEL = LIB_ROOT / "dist" / "a_stock_lib-0.5.0-py3-none-any.whl"
+
+_MISSING = f"a-stock-lib not provisioned at {LIB_ROOT}; set A_STOCK_LIB_SOURCE"
+requires_lib_wheel = pytest.mark.skipif(not LIB_WHEEL.is_file(), reason=_MISSING)
+requires_lib_checkout = pytest.mark.skipif(
+    not (LIB_ROOT / "pyproject.toml").is_file(), reason=_MISSING
+)
+
+
+def _run(args, home):
     uv = shutil.which("uv")
     assert uv
     env = {
@@ -18,20 +40,21 @@ def _run(args, home, path):
         "HOME": str(home),
         "PATH": f"{home / '.local/bin'}:{Path(uv).parent}:/usr/bin:/bin",
         "UV_OFFLINE": "1",
+        "UV_CACHE_DIR": UV_CACHE_DIR,
     }
     return subprocess.run([sys.executable, "scripts/install.py", *args], env=env, capture_output=True, text=True, check=False)
 
 
+@requires_lib_wheel
 def test_dry_run_has_no_files(tmp_path) -> None:
-    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.5.0-py3-none-any.whl"
-    result = _run(["--client", "all", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel, "--dry-run"], tmp_path, "")
+    result = _run(["--client", "all", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL), "--dry-run"], tmp_path)
     assert result.returncode == 0, result.stderr
     assert list(tmp_path.iterdir()) == []
 
 
+@requires_lib_wheel
 def test_copy_install_has_manifest_and_stable_cli(tmp_path) -> None:
-    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.5.0-py3-none-any.whl"
-    result = _run(["--client", "codex", "--mode", "copy", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel], tmp_path, "")
+    result = _run(["--client", "codex", "--mode", "copy", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL)], tmp_path)
     assert result.returncode == 0, result.stderr
     manifest = next((tmp_path / ".agents/skills/a-stock-research").glob(".a-stock-suite-manifest.json"))
     assert json.loads(manifest.read_text(encoding="utf-8"))["source_hash"]
@@ -44,9 +67,9 @@ def test_copy_install_has_manifest_and_stable_cli(tmp_path) -> None:
     assert str(Path.cwd()) not in module_path
 
 
+@requires_lib_checkout
 def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
-    lib_source = "/home/lin/a-stock-lib"
-    result = _run(["--client", "claude", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-source", lib_source], tmp_path, "")
+    result = _run(["--client", "claude", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-source", str(LIB_ROOT)], tmp_path)
     assert result.returncode == 0, result.stderr
     metadata = next((tmp_path / ".local/share/a-stock-agent/runtime").glob("*/a-stock-lib-install.json"))
     payload = json.loads(metadata.read_text(encoding="utf-8"))
@@ -55,11 +78,11 @@ def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
     assert len(payload["wheel_sha256"]) == 64
 
 
+@requires_lib_wheel
 def test_existing_skill_is_rejected_before_runtime_install(tmp_path) -> None:
-    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.5.0-py3-none-any.whl"
     target = tmp_path / ".agents/skills/a-stock-research"
     target.mkdir(parents=True)
-    result = _run(["--client", "codex", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel], tmp_path, "")
+    result = _run(["--client", "codex", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL)], tmp_path)
     assert result.returncode == 1
     assert not (tmp_path / ".local/share/a-stock-agent/runtime").exists()
 
```

### 新增文件全文：scripts/check.sh

```bash
#!/usr/bin/env bash
# Run every repository gate in one command.
#
# This repository has no git remote, so there is no hosted CI to be the source of
# truth; this script is it.  Keep docs/development.md's validation matrix in sync.
#
# Requires an `a-stock-lib` checkout or wheel.  Point A_STOCK_LIB_SOURCE at it when
# it does not sit at ~/a-stock-lib; the installer tests skip when it is absent.
set -euo pipefail
cd "$(dirname "$0")/.."

# --inexact keeps the externally provisioned a-stock-lib installed.  It is
# deliberately not a declared dependency (the installer supplies it explicitly and
# records its provenance), so a plain `uv sync --frozen` would uninstall it and
# break every runtime import.
uv sync --frozen --inexact

uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh

echo "all repository checks passed"
```

## 父级验证证据

以下均为提交方实际执行并粘贴的真实输出，不是预期值：

- 全量门禁 `bash scripts/check.sh`：
  - `613 passed in 13.76s`（改动前基线为 `2 failed, 609 passed`）
  - ruff `All checks passed!`
  - `skill validation passed`
  - `qa standalone smoke passed`
  - `cron smoke passed`
- 安装测试单独：`uv run pytest tests/test_installation.py -q` → `5 passed in 8.19s`
- 安装测试 skip 路径：`A_STOCK_LIB_SOURCE=/nonexistent uv run pytest tests/test_installation.py -q -rs` → `1 passed, 4 skipped`
- 原失败根因复现（改动前）：`uv build` 在 `HOME` 被换且 `UV_OFFLINE=1` 时报
  `No solution found when resolving: setuptools>=68 ... Because setuptools was not found in the cache`；
  仅补 `UV_CACHE_DIR` 即 `Successfully built a_stock_agent_skills-0.1.1-py3-none-any.whl`
- `uv sync --frozen --dry-run` → `Would uninstall 1 package - a-stock-lib==0.5.0`（这是改 `--inexact` 的依据）
- CLI 契约端到端（临时 `CACHE_DB_PATH`，改动后）：
  - W1 缺 `--confirm-write` → `exit=3`，且**未创建 db 文件**
  - W1 带 `--confirm-write` → 门打开，进入命令后被既有 fail-closed 校验拒绝（`data_period` 格式、无今日分析记录）
  - 零参数 `holdings` / `list` / `retro-pending` → `exit=0`
  - 子命令后置 `--flag` → `exit=2`
  - 未知命令 → `exit=1`
- 死代码删除依据：`grep -rn "apply_schema_migrations\|_invoke" src/ tests/ scripts/ skills/` 在删除后仅剩零命中

只有当前快照仍存在真实问题时才给 blocker。不要因为本批未顺带修复 `cache.py` 的整体体量（3752 行上帝模块）、手写 argv 解析、或 `DB_PATH` import 时绑定而给 blocker——这些是已识别并**明确推迟**的 P2 项。
