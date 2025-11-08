import os
from src.graph.orchestrator import run_pipeline


def test_pipeline_smoke(tmp_path):
    outdir = tmp_path.as_posix()
    res = run_pipeline("AAPL", 7, outdir, human=False)
    assert os.path.exists(res["report"])
    assert os.path.exists(res["raw"])
