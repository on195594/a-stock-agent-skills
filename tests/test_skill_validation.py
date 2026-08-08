from scripts.validate import validate


def test_three_skills_validate() -> None:
    assert validate() == []
