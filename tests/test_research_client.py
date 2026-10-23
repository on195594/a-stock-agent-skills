import pytest

from a_stock_agent_runtime import cache, research_client


def test_research_url_keeps_credentials_on_explicit_secure_endpoint():
    assert (
        research_client.endpoint_url("https://stock.keyi.win/")
        == "https://stock.keyi.win"
    )
    assert (
        research_client.endpoint_url("http://127.0.0.1:18620")
        == "http://127.0.0.1:18620"
    )
    for value in (
        "http://example.com",
        "https://user:secret@example.com",
        "https://example.com?token=secret",
        "file:///tmp/x",
    ):
        with pytest.raises(ValueError):
            research_client.endpoint_url(value)


def test_research_cli_requires_idempotency_and_does_not_open_account_db(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "absent.db"
    monkeypatch.setenv("CACHE_DB_PATH", str(path))
    monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(tmp_path / "absent.env"))
    monkeypatch.delenv("A_STOCK_RESEARCH_URL", raising=False)
    monkeypatch.delenv("A_STOCK_RESEARCH_TOKEN", raising=False)
    assert (
        cache.main(["research", "start", "600519", "--question", "现金流变化？"]) == 2
    )
    assert cache.main(["research", "reports", "600519"]) == 1
    assert "A_STOCK_RESEARCH_URL" in capsys.readouterr().err
    assert not path.exists()
