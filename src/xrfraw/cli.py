"""xrf-raw-to-h5 CLI (M3): raw MA-XRF -> NPZ/HDF5/OME-TIFF.

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
from .io import convert_file
from .processing import REBIN_TO_TARGETS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xrf-raw-to-h5",
        description="Convert raw MA-XRF files (format A/B) to NPZ/HDF5/OME-TIFF.")
    p.add_argument("input", help="raw .txt file, or a directory of raw .txt files")
    p.add_argument("-o", "--out-dir", required=True,
                   help="output directory (created if missing)")
    p.add_argument("--format", choices=("h5", "npz", "ome", "fits"), default="h5",
                   help="output format: h5, npz, ome (OME-TIFF), fits (default: h5)")
    p.add_argument("--n-channels", type=int, default=None,
                   help="exact channel depth of the output cube (default: 16384); "
                        "error if the max observed channel exceeds it")
    p.add_argument("--dtype",
                   choices=("uint32", "uint16", "float32", "float64"),
                   default="uint32",
                   help="cube dtype (default: uint32)")
    p.add_argument("--metadata", default=None,
                   help="external metadata JSON (grid/calibration; format B needs it)")
    p.add_argument("--rebin", nargs=2, metavar=("SIZE", "HOW"), default=None,
                   help="explicit rebin along channel: SIZE >= 2, HOW sum|mean (default: off)")
    p.add_argument("--rebin-to", type=int, default=None,
                   help="rebin channel axis to exact depth (512/1024/2048/4096/8192); "
                        "sum-only, totals preserved (default: off)")
    p.add_argument("--compress", type=int, default=4,
                   help="compression level 0-9: gzip per h5/npz, zlib per ome "
                        "(0 = none; default: 4)")
    p.add_argument("--overwrite", action="store_true",
                   help="replace existing output files")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _convert_one(src: Path, out_dir: Path, args, rebin_spec) -> None:
    ext = "ome.tif" if args.format == "ome" else args.format
    convert_file(src, out_dir / f"{src.stem}.{ext}",
                 fmt=args.format, n_channels=args.n_channels, dtype=args.dtype,
                 metadata=args.metadata, rebin_spec=rebin_spec,
                 rebin_to=args.rebin_to, compress=args.compress,
                 overwrite=args.overwrite)


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

    if args.rebin_to is not None and args.rebin:
        print("error: pass either --rebin or --rebin-to, not both", file=sys.stderr)
        return 2
    if args.rebin_to is not None and args.rebin_to not in REBIN_TO_TARGETS:
        print(f"error: --rebin-to must be one of {REBIN_TO_TARGETS}, got {args.rebin_to}",
              file=sys.stderr)
        return 2
    if not 0 <= args.compress <= 9:
        print(f"error: --compress must be an int 0..9, got {args.compress}",
              file=sys.stderr)
        return 2

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