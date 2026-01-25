import builtins
import types
import pytest

import src.cli as cli


def test_cli_success(monkeypatch, capsys):
    # Arrange: fake run_pipeline success
    def fake_run_pipeline(symbol, days, outdir, human=False):
        return {"report": "artifacts/MSFT/report.md", "plot": "artifacts/MSFT/chart.png"}

    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)

    # Fake argv
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--symbol", "MSFT", "--days", "5", "--outdir", "artifacts", "--human", "false"],
    )

    # Act
    cli.main()

    # Assert: outputs printed
    out = capsys.readouterr().out
    assert "== Outputs ==" in out
    assert "report: artifacts/MSFT/report.md" in out


def test_cli_error_path(monkeypatch, capsys):
    # Arrange: fake run_pipeline error payload
    def fake_run_pipeline(symbol, days, outdir, human=False):
        return {"status": "error", "reason": "Strict mode abort", "suggested_action": "Disable strict_mode"}

    monkeypatch.setattr(cli, "run_pipeline", fake_run_pipeline)

    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--symbol", "META", "--days", "5", "--outdir", "artifacts", "--human", "false"],
    )

    # Act
    cli.main()

    # Assert
    out = capsys.readouterr().out
    assert "[ERROR] Strict mode abort" in out
    assert "Suggestion: Disable strict_mode" in out
