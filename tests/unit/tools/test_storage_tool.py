import os
from src.tools.storage_tool import save_json, save_markdown


def test_save_json_and_markdown(tmp_path):
    outdir = tmp_path / "artifacts"
    outdir.mkdir()

    save_json({"a": 1}, str(outdir), "x.json")
    save_markdown("# title", str(outdir), "x.md")

    assert (outdir / "x.json").exists()
    assert (outdir / "x.md").exists()
