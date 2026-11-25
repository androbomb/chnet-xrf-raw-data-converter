from importlib.metadata import version

import xrfraw


def test_version():
    # equalità col dist installato: becca il drift del fallback in __init__.py
    assert xrfraw.__version__ == version("chnet-xrf-raw-data-converter")


def test_public_api():
    assert callable(xrfraw.read_raw)
    assert callable(xrfraw.inspect_raw)
    assert hasattr(xrfraw, "Dataset")