import shutil
from pathlib import Path

import pytest

from scripts.validate import validate


ROOT = Path(__file__).resolve().parents[1]


def _copy_skills(tmp_path: Path) -> Path:
    shutil.copytree(
        ROOT / "skills",
        tmp_path / "skills",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    return tmp_path / "skills/a-stock-research/SKILL.md"


def test_three_skills_validate() -> None:
    assert validate() == []


def test_installed_content_excludes_mutable_files_and_ignores_bytecode(
    tmp_path,
) -> None:
    mutable = (
        "cache.db",
        "cache.db-wal",
        "cache.db-shm",
        ".env",
        ".env.local",
        "nested/logs/run.log",
        "nested/locks/runtime.lock",
    )
    for name in mutable:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\x00")
    for name in ("__pycache__/module.pyc", "module.pyo"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("/home/example/.agents/skills", encoding="utf-8")
    (tmp_path / "logs.md").write_text("Documentation is not runtime state.")

    assert set(validate(installed_root=tmp_path)) == {
        f"mutable file packaged: {tmp_path / name}" for name in mutable
    }


def test_client_specific_command_in_reference_is_rejected(tmp_path) -> None:
    _copy_skills(tmp_path)
    reference = tmp_path / "skills/a-stock-research/references/client-command.md"
    reference.write_text("agy --prompt report", encoding="utf-8")
    errors = validate(tmp_path)
    assert any("client-specific tool invocation" in error for error in errors)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda text: text + "\n" + "x" * 13_000, "exceeds main-file budget"),
        (
            lambda text: text + "\n[broken](references/missing.md)\n",
            "missing or invalid reference",
        ),
        (lambda text: text.replace("fail-closed", "closed"), "missing fail-closed"),
        (
            lambda text: text + "\nROE >= 15% 时通过。\n",
            "deterministic threshold duplicated",
        ),
    ],
)
def test_thin_skill_regression_is_rejected(tmp_path, mutation, message) -> None:
    skill = _copy_skills(tmp_path)
    skill.write_text(mutation(skill.read_text(encoding="utf-8")), encoding="utf-8")

    assert any(message in error for error in validate(tmp_path))


def test_copied_skill_suite_needs_no_repository_docs(tmp_path) -> None:
    _copy_skills(tmp_path)
    assert validate(tmp_path) == []


@pytest.mark.parametrize("link", ["missing.md", "../../../README.md"])
@pytest.mark.parametrize("title", ["", ' "资料标题"', " '资料标题'", " (资料标题)"])
def test_reference_markdown_links_cannot_escape_the_package_suite(
    tmp_path, link, title
):
    _copy_skills(tmp_path)
    (tmp_path / "README.md").write_text("This exists only in the source repository.")
    reference = tmp_path / "skills/a-stock-research/references/extra.md"
    reference.write_text(f"[reference]({link}{title})")
    assert any("nonportable or missing Markdown link" in e for e in validate(tmp_path))


@pytest.mark.parametrize("title", ["", ' "资料标题"', " '资料标题'", " (资料标题)"])
def test_reference_links_allow_sibling_skills_urls_and_fragments(tmp_path, title):
    _copy_skills(tmp_path)
    reference = tmp_path / "skills/a-stock-research/references/extra.md"
    reference.write_text(
        f"[sibling](../../a-stock-monitor/SKILL.md#路由{title})\n"
        f"[web](https://example.com/source{title}) [anchor](#local{title})\n"
    )
    assert validate(tmp_path) == []
