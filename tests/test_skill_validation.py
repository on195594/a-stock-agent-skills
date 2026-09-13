import shutil
from pathlib import Path

import pytest

from scripts.validate import validate


ROOT = Path(__file__).resolve().parents[1]


def _copy_skills(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "skills", tmp_path / "skills")
    return tmp_path / "skills/a-stock-research/SKILL.md"


def test_three_skills_validate() -> None:
    assert validate() == []


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
