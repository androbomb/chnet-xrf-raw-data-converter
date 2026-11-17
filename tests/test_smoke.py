import xrfraw


def test_version():
    assert xrfraw.__version__ == "0.1.0"


def test_public_api():
    assert callable(xrfraw.read_raw)
    assert callable(xrfraw.inspect_raw)
    assert hasattr(xrfraw, "Dataset")