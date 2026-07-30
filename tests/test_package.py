"""Baseline smoke tests. Expand alongside real oracle/core implementation."""

import oracle


def test_version_is_defined():
    assert isinstance(oracle.__version__, str)
    assert oracle.__version__ != ""
