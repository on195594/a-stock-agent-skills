from a_stock_agent_runtime import cache
from a_stock_agent_runtime.cache import COMMANDS, COMMAND_CLASSIFICATION


def test_every_cache_command_has_one_classification() -> None:
    assert set(COMMANDS) == set(COMMAND_CLASSIFICATION)
    assert set(COMMAND_CLASSIFICATION.values()) <= {"R0", "R1", "W1"}
    assert all(list(COMMAND_CLASSIFICATION.values()).count(name) >= 1 for name in ("R0", "R1", "W1"))


def test_help_documents_every_command() -> None:
    """`--help` prints this docstring, so it must not drift from the command table."""
    assert cache.__doc__
    assert [name for name in COMMANDS if name not in cache.__doc__] == []


def test_help_states_the_write_gate_and_lists_every_w1_command() -> None:
    """The confirmation gate is the only write protection; help must not omit it."""
    gate_section, _, _ = cache.__doc__.partition("子命令：")
    assert "--confirm-write" in gate_section
    w1 = [name for name, level in COMMAND_CLASSIFICATION.items() if level == "W1"]
    assert [name for name in w1 if name not in gate_section] == []
