"""xrf-raw-to-h5 CLI (M3): raw MA-XRF -> NPZ/HDF5.

Core pipeline (output_schema.md): read_raw -> with_calibration (when m/q
known) -> optional explicit rebin -> write_dataset.
Exit codes: 0 ok, 1 one or more inputs failed, 2 usage error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tqdm import tqdm

from . import __version__
from .data import read_raw
from .io import write_dataset
from .processing import rebin, with_calibration


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xrf-raw-to-h5",
        description="Convert raw MA-XRF files (format A/B) to NPZ/HDF5.")
    p.add_argument("input", help="raw .txt file, or a directory of raw .txt files")
    p.add_argument("-o", "--out-dir", required=True,
                   help="output directory (created if missing)")
    p.add_argument("--format", choices=("h5", "npz"), default="h5",
                   help="output format (default: h5)")
    p.add_argument("--n-channels", type=int, default=None,
                   help="explicit channel depth (default: 16384)")
    p.add_argument("--dtype", choices=("uint32", "uint16"), default="uint32",
                   help="cube dtype (default: uint32)")
    p.add_argument("--metadata", default=None,
                   help="external metadata JSON (grid/calibration; format B needs it)")
    p.add_argument("--rebin", nargs=2, metavar=("SIZE", "HOW"), default=None,
                   help="explicit rebin along channel: SIZE >= 2, HOW sum|mean (default: off)")
    p.add_argument("--overwrite", action="store_true",
                   help="replace existing output files")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _convert_one(src: Path, out_dir: Path, args, rebin_spec) -> None:
    kwargs = {"dtype": args.dtype}
    if args.n_channels is not None:
        kwargs["n_channels"] = args.n_channels
    if args.metadata:
        kwargs["metadata"] = args.metadata
    ds = read_raw(src, **kwargs)
    cal = ds.metadata.get("known_calibration")
    if cal:
        ds = with_calibration(ds, cal["m"], cal["q"], provenance=cal["provenance"])
    if rebin_spec:
        ds = rebin(ds, rebin_spec[0], how=rebin_spec[1])
    write_dataset(ds, out_dir / f"{src.stem}.{args.format}",
                  fmt=args.format, overwrite=args.overwrite)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    rebin_spec = None
    if args.rebin:
        try:
            size = int(args.rebin[0])
            how = args.rebin[1]
        except ValueError:
            print(f"error: --rebin SIZE must be an integer, got {args.rebin[0]!r}",
                  file=sys.stderr)
            return 2
        if size < 2 or how not in ("sum", "mean"):
            print(f"error: --rebin expects SIZE >= 2 and HOW in sum|mean, got {args.rebin}",
                  file=sys.stderr)
            return 2
        rebin_spec = (size, how)

    src = Path(args.input)
    if src.is_dir():
        files = sorted(src.glob("*.txt"))
    elif src.is_file():
        files = [src]
    else:
        print(f"error: input not found: {src}", file=sys.stderr)
        return 1
    if not files:
        print(f"error: no .txt files in {src}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = 0
    for f in tqdm(files, desc="convert", unit="file"):
        try:
            _convert_one(f, out_dir, args, rebin_spec)
        except Exception as e:  # report and continue the batch
            failed += 1
            print(f"error: {f.name}: {e}", file=sys.stderr)
    if failed:
        print(f"{failed}/{len(files)} files failed", file=sys.stderr)
        return 1
    return 0