"""M2 processing: with_calibration (F3), rebin (F4), count preservation (F2)."""
import numpy as np
import pytest

from _synthetic import GRID32, PIXELS, write_format_a, write_format_b
from xrfraw import Dataset, read_raw, rebin, with_calibration


def _mini_ds(nc=8, dtype=np.uint32, seed=0, mask_all=True):
    """Small (3, 4, nc) dataset built directly (no raw file needed)."""
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 100, size=(3, 4, nc)).astype(dtype)
    mask = np.ones((3, 4), dtype=bool)
    if not mask_all:
        mask[0, 0] = False
    total = int(img.sum())
    return Dataset(
        img=img,
        channel=np.arange(nc, dtype=np.uint32),
        x_axis=np.arange(4, dtype=np.float64) * 1000.0,
        y_axis=np.arange(3, dtype=np.float64) * 5000.0,
        mask=mask,
        metadata={"schema_version": 1, "n_channels": nc, "dtype": str(img.dtype),
                  "n_events": total, "transforms": []},
        source_file="t.txt",
        n_events=total,
    )


# --- F3: with_calibration = pure attachment ---------------------------------

def test_with_calibration_element_identical(tmp_path):
    p = tmp_path / "s.a.txt"
    write_format_a(p, GRID32, PIXELS)
    ds = read_raw(p)
    m, q = 1.5, -0.25
    ds2 = with_calibration(ds, m, q, provenance="xml")
    # counts bitwise-identical (no resampling, no crop, no overwrite)
    assert ds2.img.dtype == ds.img.dtype
    assert ds2.img.tobytes() == ds.img.tobytes()
    assert ds2.calibrated and ds2.calibration_m == m and ds2.calibration_q == q
    assert ds2.energy.shape == (16384,) and ds2.energy.dtype == np.float64
    # unapplied known_calibration is replaced by the applied calibration
    assert "known_calibration" not in ds2.metadata
    assert ds2.metadata["calibration"] == {"m": m, "q": q, "provenance": "xml"}
    assert ds2.metadata["transforms"] == []  # calibration is core, not a transform
    # input not mutated
    assert not ds.calibrated and ds.energy is None
    assert ds.metadata["known_calibration"] == {"m": m, "q": q, "provenance": "xml"}


def test_with_calibration_hand_10_channels(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, list(range(10)))])
    ds = read_raw(p, n_channels=10)
    m, q = 0.5, -1.0
    ds2 = with_calibration(ds, m, q, provenance="user")
    expected = np.array([-1.0 + 0.5 * i for i in range(10)])
    np.testing.assert_array_equal(ds2.energy, expected)  # exact, bit-for-bit
    assert ds2.img.tobytes() == ds.img.tobytes()


def test_with_calibration_validation(tmp_path):
    p = tmp_path / "s.b.txt"
    write_format_b(p, [(0, 0, [1])])
    ds = read_raw(p, n_channels=16)
    with pytest.raises(ValueError, match="finite"):
        with_calibration(ds, float("nan"), 0.0, provenance="user")
    with pytest.raises(ValueError, match="m must be > 0"):
        with_calibration(ds, 0.0, 0.0, provenance="user")
    with pytest.raises(ValueError, match="m must be > 0"):
        with_calibration(ds, -1.0, 0.0, provenance="user")
    with pytest.raises(ValueError, match="provenance"):
        with_calibration(ds, 1.0, 0.0, provenance="device")


# --- F4: rebin (explicit, uniform groups) ------------------------------------

def test_rebin_sum_preserves_totals():
    ds = _mini_ds(nc=8)
    out = rebin(ds, 2)
    assert out.img.shape == (3, 4, 4)
    assert out.img.dtype == np.uint32
    assert int(out.img.sum()) == ds.n_events  # sum preserves totals (F4)
    for i in range(4):
        np.testing.assert_array_equal(
            out.img[..., i], ds.img[..., 2 * i:2 * i + 2].sum(axis=2))
    assert out.channel.tolist() == [0, 2, 4, 6]  # first index of each group
    np.testing.assert_array_equal(out.mask, ds.mask)
    assert out.metadata["n_channels"] == 4
    assert out.metadata["dtype"] == "uint32"
    assert out.metadata["transforms"] == [
        {"type": "rebin", "size": 2, "how": "sum",
         "n_channels_from": 8, "n_channels_to": 4}]
    # input not mutated
    assert ds.img.shape == (3, 4, 8) and ds.metadata["transforms"] == []


def test_rebin_mean_is_group_average():
    ds = _mini_ds(nc=8, seed=1)
    out = rebin(ds, 2, how="mean")
    assert out.img.dtype == np.float64
    expected = ds.img.astype(np.float64).reshape(3, 4, 4, 2).mean(axis=3)
    np.testing.assert_array_equal(out.img, expected)  # sum/width per bin (F4)
    assert out.metadata["dtype"] == "float64"
    assert out.metadata["transforms"][0]["how"] == "mean"


def test_rebin_args_and_divisibility():
    ds = _mini_ds(nc=8)
    with pytest.raises(ValueError, match="does not divide"):
        rebin(ds, 3)
    with pytest.raises(ValueError, match="size"):
        rebin(ds, 1)
    with pytest.raises(ValueError, match="size"):
        rebin(ds, "2")
    with pytest.raises(ValueError, match="size"):
        rebin(ds, True)
    with pytest.raises(ValueError, match="how"):
        rebin(ds, 2, how="max")


def test_rebin_uint16_upcast():
    ds = _mini_ds(nc=4, dtype=np.uint16)
    out = rebin(ds, 2)
    assert out.img.dtype == np.uint32  # sums may exceed uint16
    assert int(out.img.sum()) == ds.n_events


def test_rebin_chained_and_calibrated():
    ds = with_calibration(_mini_ds(nc=8, seed=2), 0.25, -0.5, provenance="user")
    out = rebin(rebin(ds, 2), 2)
    assert out.img.shape[2] == 2
    assert out.calibrated and out.calibration_m == 0.25
    # energy follows the output channel axis (first index of each group)
    assert out.energy.tolist() == ds.energy[[0, 4]].tolist()
    assert [t["size"] for t in out.metadata["transforms"]] == [2, 2]


def test_rebin_sum_overflow_guard():
    ds = _mini_ds(nc=4)
    ds.img[0, 0, :] = 1_200_000_000  # 4 x 1.2e9 = 4.8e9 > uint32 max
    ds.n_events = int(ds.img.sum())
    with pytest.raises(ValueError, match="overflows uint32"):
        rebin(ds, 4)
    # below the limit the same shape works
    ds.img[0, 0, :] = 1_000_000_000  # 4e9 < 4294967295
    ds.n_events = int(ds.img.sum())
    out = rebin(ds, 4)
    assert out.img.shape == (3, 4, 1)
    assert int(out.img[0, 0, 0]) == 4_000_000_000