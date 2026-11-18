"""xrfraw.__version__ deve uguagliare i metadati del dist installato."""

from importlib.metadata import version

import xrfraw


def test_version_matches_distribution_metadata():
    assert xrfraw.__version__ == version("chnet-xrf-raw-data-converter")