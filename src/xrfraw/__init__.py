"""xrfraw — raw MA-XRF (Fi MA-XRF, INFN-CHNet) to NPZ/HDF5/OME-TIFF/FITS converter.

No side effects on import. See README.md and the docs at the repository root.
"""

from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    # mai hardcodato: deriva dai metadati del dist installato (no drift)
    __version__ = _dist_version("chnet-xrf-raw-data-converter")
except PackageNotFoundError:  # checkout di sorgente non installato
    __version__ = "0.1.3"

from .dataset import Dataset
from .data import inspect_raw, read_raw
from .fits import read_fits
from .ome import read_ome
from .processing import rebin, rebin_to, with_calibration

__all__ = ["Dataset", "__version__", "inspect_raw", "read_fits", "read_ome",
           "read_raw", "rebin", "rebin_to", "with_calibration"]
