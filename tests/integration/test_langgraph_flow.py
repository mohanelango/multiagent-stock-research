from unittest.mock import MagicMock
import src.graph.orchestrator as orchestrator


def test_build_graph_executes_nodes_in_order(monkeypatch, minimal_cfg, sample_bundle_upper, tmp_path):
    calls = []

    # Stub agent run methods at class level so build_graph instances use them.
    monkeypatch.setattr("src.agents.data_agent.DataAgent.run", lambda self, symbol, days: (calls.append("data"), sample_bundle_upper)[1])
    monkeypatch.setattr("src.agents.analyst_agent.AnalystAgent.run", lambda self, bundle, days: (calls.append("analyst"), "ANALYST_NOTE")[1])
    monkeypatch.setattr("src.agents.compliance_agent.ComplianceAgent.run", lambda self, note: (calls.append("compliance"), "FINAL_NOTE")[1])

    # Avoid heavy dependencies during test
    monkeypatch.setattr("src.tools.plot_tool.save_price_plot", lambda dates, closes, currency, path: (calls.append("plot"), str(tmp_path / "x.png"))[1])
    monkeypatch.setattr("src.tools.storage_tool.save_markdown", lambda md, outdir, filename: calls.append("save_md"))
    monkeypatch.setattr("src.tools.storage_tool.save_json", lambda bundle, outdir, filename: calls.append("save_json"))
    monkeypatch.setattr("pypandoc.convert_text", lambda *a, **k: calls.append("pdf"))

    app = orchestrator.build_graph(minimal_cfg, fmp_api_key="demo")
    state = {"symbol": "AAPL", "days": 5, "outdir": str(tmp_path)}
    app.invoke(state)

    # Ensures agent-to-agent communication + publish happens
    assert calls[:3] == ["data", "analyst", "compliance"]
    assert "data" in calls
    assert "analyst" in calls
