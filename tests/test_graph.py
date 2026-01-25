import os
from src.graph.orchestrator import run_pipeline


def test_pipeline_smoke(tmp_path):
    outdir = tmp_path.as_posix()
    res = run_pipeline("AAPL", 3, outdir, human=False)
    print('--->',res)
    assert "report" in res
