"""Slow tests on the real data_example/ files (run: pytest -m slow)."""
from pathlib import Path

import pytest

from xrfraw import inspect_raw

BASE = Path(__file__).resolve().parents[1] / "data_example"
MAPPA11 = BASE / "mappa11.txt"
RAGAZZO = BASE / "Ragazzo-triste_area4_centrodx_38-80.txt"


@pytest.mark.slow
@pytest.mark.skipif(not (MAPPA11.is_file() and RAGAZZO.is_file()),
                    reason="data_example/ files not present")
def test_inspect_real_files():
    r = inspect_raw(MAPPA11)
    assert r["ok"] and r["format"] == "xml"
    assert r["n_events"] == 19_825_090
    assert r["max_channel"] == 15902
    assert r["grid"] == {"x_min": 5000, "x_max": 290000, "x_step": 1000,
                         "y_min": 190000, "y_max": 265000, "y_step": 1000}
    assert r["n_pixels"] == 286 * 76
    assert r["n_pixels_acquired"] == 21_659
    mc = [a for a in r["anomalies"] if a["type"] == "missing_column"]
    assert [a["x"] for a in mc] == [290000] and mc[0]["n_pixels"] == 76
    assert any(a["type"] == "missing_row" and a["x"] == 5000 and a["y"] == 265000
               for a in r["anomalies"])
    dx = [a for a in r["anomalies"] if a["type"] == "dangling_x_marker"]
    assert len(dx) == 1 and dx[0]["x"] == 5000 and dx[0]["y_prev"] == 265000 \
        and dx[0].get("at") == "eof"

    r2 = inspect_raw(RAGAZZO)
    assert r2["ok"] and r2["format"] == "data-only"
    assert r2["n_events"] == 56_661_209
    assert r2["max_channel"] == 15999
    assert r2["grid_source"] == "inferred"
    assert r2["grid"] == {"x_min": 5000, "x_max": 219000, "x_step": 1000,
                          "y_min": 5000, "y_max": 149000, "y_step": 1000}
    assert r2["n_pixels"] == 215 * 145
    assert r2["n_pixels_acquired"] == 31_174
    assert any(a["type"] == "dangling_x_marker" and a["at"] == "eof" and a["x"] == 219000
               and a["y_prev"] == 149000 for a in r2["anomalies"])
