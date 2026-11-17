"""xrfraw — raw MA-XRF (Fi MA-XRF, INFN-CHNet) to NPZ/HDF5 converter.

No side effects on import. See README.md and the docs at the repository root.
"""

__version__ = "0.1.0"

from .dataset import Dataset
from .data import inspect_raw, read_raw
from .processing import rebin, rebin_to, with_calibration

__all__ = ["Dataset", "__version__", "inspect_raw", "read_raw", "rebin",
           "rebin_to", "with_calibration"]
