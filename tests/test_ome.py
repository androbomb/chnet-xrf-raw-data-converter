"""OME-TIFF: round-trip lossless (valori/shape/dtype/metadata), OME-XML,
BigTIFF, canali molti, compressione, CLI, errori (schema: output_schema.md)."""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import tifffile

from _synthetic import GRID32, N_EVENTS, PIXELS, write_format_a, write_format_b
from xrfraw import read_raw, read_ome, rebin, with_calibration
from xrfraw.io import write_dataset
from xrfraw.ome import write_ome

_OME = "http://www.openmicroscopy.org/Schemas/OME/2016-06"
_ANN = "urn:xrfraw:v1"


def _dataset(tmp_path, src="a", dtype="uint32", calibrated=False):
    p = tmp_path / f"{src}.txt"
    if src == "a":
        write_format_a(p, GRID32, PIXELS)
    else:
        write_format_b(p, PIXELS)
    ds = read_raw(p, n_channels=16, dtype=dtype)
    return with_calibration(ds, 1.5, -0.25, provenance="xml") if calibrated else ds


def _assert_same(ds, back):
    np.testing.assert_array_equal(back.img, ds.img)
    assert back.img.shape == ds.img.shape
    assert back.img.dtype == ds.img.dtype
    np.testing.assert_array_equal(back.channel, ds.channel)
    np.testing.assert_array_equal(back.x_axis, ds.x_axis)
    np.testing.assert_array_equal(back.y_axis, ds.y_axis)
    np.testing.assert_array_equal(back.mask, ds.mask)
    assert back.metadata == ds.metadata
    assert (back.source_file, back.n_events, back.calibrated) == \
        (ds.source_file, ds.n_events, ds.calibrated)
    if ds.energy is not None:
        np.testing.assert_array_equal(back.energy, ds.energy)
        assert (back.calibration_m, back.calibration_q) == \
            (ds.calibration_m, ds.calibration_q)


def test_round_trip_calibrated(tmp_path):
    ds = _dataset(tmp_path, calibrated=True)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    back = read_ome(out)
    _assert_same(ds, back)
    np.testing.assert_array_equal(back.energy, 1.5 * back.channel + -0.25)


def test_round_trip_uncalibrated(tmp_path):
    ds = _dataset(tmp_path, dtype="float32")
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    back = read_ome(out)
    _assert_same(ds, back)
    assert back.energy is None and not back.calibrated


@pytest.mark.parametrize("dtype", ["uint16", "uint32", "float32", "float64"])
def test_round_trip_dtype(tmp_path, dtype):
    ds = _dataset(tmp_path, dtype=dtype, calibrated=True)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    _assert_same(ds, read_ome(out))


def test_round_trip_format_b(tmp_path):
    ds = _dataset(tmp_path, src="b")
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    _assert_same(ds, read_ome(out))


def test_omexml_structure(tmp_path):
    ds = _dataset(tmp_path, calibrated=True)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    ny, nx, nc = ds.img.shape
    with tifffile.TiffFile(str(out)) as tf:
        assert len(tf.pages) == nc
        assert all(pg.shape == (ny, nx) for pg in tf.pages)  # CYX: mai RGB/3D
        assert tf.pages[0].dtype == np.dtype(ds.img.dtype)
        root = ET.fromstring(tf.ome_metadata)
    px = root.find(f"{{{_OME}}}Image/{{{_OME}}}Pixels")
    assert px is not None
    assert px.get("Type") == "uint32"
    assert px.get("DimensionOrder") == "XYZCT"  # 2016-06: enum valido, no DimensionType
    assert (px.get("SizeC"), px.get("SizeY"), px.get("SizeX")) == (str(nc), str(ny), str(nx))
    assert float(px.get("PhysicalSizeX")) == float(GRID32[2])  # x_step
    assert px.get("PhysicalSizeXUnit") == ds.metadata["units"]["x"]
    chans = px.findall(f"{{{_OME}}}Channel")
    assert len(chans) == nc and all(c.get("SamplesPerPixel") == "1" for c in chans)
    sa = next((a for a in root.iter(f"{{{_OME}}}MapAnnotation")
               if a.get("Namespace") == _ANN), None)
    assert sa is not None and sa.get("ID") == "Annotation:0"
    val = sa.find(f"{{{_OME}}}Value")
    assert val is not None
    ms = val.findall(f"{{{_OME}}}M")
    assert {m.get("K") for m in ms} == {"meta", "attrs", "mask"}
    meta_txt = next((m.text or "") for m in ms if m.get("K") == "meta")
    assert json.loads(meta_txt)["n_events"] == N_EVENTS


def test_single_ome_series_no_shaped(tmp_path):
    # audit: un'unica serie OME CYX, NON N serie shaped YX per piano
    ds = _dataset(tmp_path, calibrated=True)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    ny, nx, nc = ds.img.shape
    with tifffile.TiffFile(str(out)) as tf:
        assert tf.is_ome
        assert not tf.is_shaped
        assert len(tf.series) == 1
        assert tf.series[0].axes == "CYX"
        assert tf.series[0].shape == (nc, ny, nx)
    back = read_ome(out)
    assert int(back.img.sum()) == int(ds.img.sum())  # counts conservati
    assert back.n_events == ds.n_events
    assert back.metadata == ds.metadata  # annotazioni conservate
    np.testing.assert_array_equal(back.mask, ds.mask)
    np.testing.assert_array_equal(back.energy, ds.energy)


def test_ome_energy_post_rebin(tmp_path):
    # la calibrazione energetica registrata e' quella post-rebinning
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = with_calibration(read_raw(p, n_channels=16), 1.5, -0.25, provenance="xml")
    d2 = rebin(ds, size=4, how="sum")  # 16 -> 4 canali, m' = 1.5*4 = 6
    out = write_dataset(d2, tmp_path / "r.ome.tif", fmt="ome")
    back = read_ome(out)
    assert back.calibration_m == pytest.approx(6.0)
    np.testing.assert_array_equal(back.energy, d2.energy)
    assert int(back.img.sum()) == int(d2.img.sum())


def test_bigtiff(tmp_path):
    ds = _dataset(tmp_path)
    out = write_ome(ds, tmp_path / "c.ome.tif", bigtiff=True)
    with open(out, "rb") as f:
        assert f.read(4) == b"II\x2b\x00"  # magic BigTIFF
    _assert_same(ds, read_ome(out))


def test_many_channels(tmp_path):
    p = tmp_path / "a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = read_raw(p, n_channels=256)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome")
    back = read_ome(out)
    _assert_same(ds, back)
    assert back.img.shape == (*ds.img.shape[:2], 256)


@pytest.mark.parametrize("compress", [0, 9])
def test_compression_lossless(tmp_path, compress):
    ds = _dataset(tmp_path, calibrated=True)
    out = write_dataset(ds, tmp_path / "c.ome.tif", fmt="ome", compress=compress)
    _assert_same(ds, read_ome(out))


def test_read_plain_tiff_raises(tmp_path):
    p = tmp_path / "plain.tif"
    with tifffile.TiffWriter(str(p)) as tw:
        tw.write(np.zeros((4, 5), dtype=np.uint16))
    with pytest.raises(ValueError, match="OME-XML"):
        read_ome(p)


def test_cli_ome(tmp_path):
    a = tmp_path / "a.txt"
    write_format_a(a, GRID32, PIXELS)
    r = subprocess.run([sys.executable, "-m", "xrfraw", a, "-o", tmp_path / "out",
                        "--format", "ome", "--n-channels", "16"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "out" / "a.ome.tif"
    assert out.is_file()
    back = read_ome(out)
    assert back.n_events == N_EVENTS
    assert back.img.shape[2] == 16