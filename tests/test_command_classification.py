from a_stock_agent_runtime.cache import COMMANDS, COMMAND_CLASSIFICATION


def test_every_cache_command_has_one_classification() -> None:
    assert set(COMMANDS) == set(COMMAND_CLASSIFICATION)
    assert set(COMMAND_CLASSIFICATION.values()) <= {"R0", "R1", "W1"}
    assert all(list(COMMAND_CLASSIFICATION.values()).count(name) >= 1 for name in ("R0", "R1", "W1"))
