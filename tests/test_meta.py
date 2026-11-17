"""Metadata: XML header parsing and external metadata merge."""
import pytest

from xrfraw.data.meta import load_metadata, merge_metadata, parse_xml_header
from xrfraw.errors import MetadataConflictError

HEADER_LINES = [
    '<?xml version="1.2" encoding="UTF-8"?>',
    "<XRFanalysis>",
    "\t<tube>",
    '\t\t<tubeVoltage(kV)>"35"</tubeVoltage(kV)>',
    '\t\t<tubeCurrent(uA)>"100"</tubeCurrent(uA)>',
    "\t</tube>",
    "\t<calibration>",
    '\t\t<calibration_keV/ch>"0.00259259"</calibration_keV/ch>',
    '\t\t<calibration_Offset>"-0.0355556"</calibration_Offset>',
    "\t</calibration>",
    "\t<coll>",
    '\t\t<Collimator Diameter (mm)>"0.8"</Collimator Diameter (mm)>',
    "\t</coll>",
    "\t<analysisInfo>",
    '\t\t<Xmin>"5000"</Xmin>',
    '\t\t<Xmax>"290000"</Xmax>',
    '\t\t<Ymin>"190000"</Ymin>',
    '\t\t<Ymax>"265000"</Ymax>',
    '\t\t<Xstep>"1000"</Xstep>',
    '\t\t<Ystep>"1000"</Ystep>',
    '\t\t<Velocity>"8000"</Velocity>',
    "\t</analysisInfo>",
    "\t<analysisData>",
]


def test_parse_xml_header():
    meta = parse_xml_header(HEADER_LINES)
    assert meta["m"] == 0.00259259 and meta["q"] == -0.0355556
    assert meta["velocity"] == 8000
    assert meta["grid"] == {"x_min": 5000, "x_max": 290000, "x_step": 1000,
                            "y_min": 190000, "y_max": 265000, "y_step": 1000}
    assert meta["raw"]["tube.tubeVoltage(kV)"] == 35
    assert meta["raw"]["coll.Collimator Diameter (mm)"] == 0.8


def test_parse_xml_header_no_calibration():
    lines = [l for l in HEADER_LINES if "calibration" not in l or "calibration_" in l]
    meta = parse_xml_header(["\t<analysisData>"])
    assert meta["m"] is None and meta["q"] is None and meta["grid"] is None


def test_merge_external_fills_missing():
    merged = merge_metadata({"raw": {}}, {"calibration": {"m": 2.0, "q": -1.0}})
    assert merged["m"] == 2.0 and merged["q"] == -1.0


def test_merge_conflict_raises():
    base = {"m": 1.5, "q": -0.25}
    with pytest.raises(MetadataConflictError):
        merge_metadata(base, {"calibration": {"m": 2.0, "q": -0.25}})


def test_merge_grid_conflict_raises():
    base = {"grid": {"x_min": 0, "x_max": 2000, "x_step": 1000,
                     "y_min": 0, "y_max": 5000, "y_step": 5000}}
    with pytest.raises(MetadataConflictError):
        merge_metadata(base, {"grid": {"x_min": 999}})


def test_load_metadata_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_metadata(tmp_path / "nope.json")
