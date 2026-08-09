import shutil
from pathlib import Path

from scripts.validate import validate


def test_three_skills_validate() -> None:
    assert validate() == []


def test_client_specific_command_in_reference_is_rejected(tmp_path) -> None:
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "skills", tmp_path / "skills")
    reference = tmp_path / "skills/a-stock-research/references/client-command.md"
    reference.write_text("agy --prompt report", encoding="utf-8")
    errors = validate(tmp_path)
    assert any("client-specific tool invocation" in error for error in errors)
