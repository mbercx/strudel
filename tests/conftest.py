"""Project-wide pytest fixtures & hooks.

Docs: https://docs.pytest.org/en/stable/how-to/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _get_equally_spaced(array, max_number):
    """Return `max_number` equally spaced elements from `array`."""
    if max_number <= 1:
        return [array[0]] if array else []

    try:
        import numpy as np

        indices = np.linspace(0, len(array) - 1, max_number, dtype=int)
    except ImportError:
        step = (len(array) - 1) / (max_number - 1)
        indices = [round(i * step) for i in range(max_number)]

    if isinstance(array, (list, tuple)):
        return [array[i] for i in indices]
    return array[indices]


def _serialize(item, max_number=None):
    """Recursively make `item` JSON-serializable for regression tests.

    Supported conversions:

    - `str`, `bool`: returned as-is.
    - `float`, `int`: converted to float rounded to 5 digits.
    - `list`, `tuple`: recursed; subsampled to `max_number` elements when set.
    - `numpy.ndarray`: complex arrays split into `[real, imag]` lists; others
      converted via `.tolist()`. Subsampled when `max_number` is set.
    - `dict`: recursed on values.
    """
    if isinstance(item, (str, bool)):
        return item
    if isinstance(item, dict):
        return {k: _serialize(v, max_number) for k, v in item.items()}
    if isinstance(item, (list, tuple)):
        serialized = [_serialize(el, max_number) for el in item]
        if max_number is not None and len(serialized) > max_number:
            serialized = _get_equally_spaced(serialized, max_number)
        return serialized

    try:
        import numpy as np

        if isinstance(item, np.integer):
            return round(float(item), 5)
        if isinstance(item, np.floating):
            return round(float(item), 5)
        if isinstance(item, np.ndarray):
            if np.iscomplexobj(item):
                return [
                    _serialize(item.real, max_number),
                    _serialize(item.imag, max_number),
                ]
            if max_number is not None and item.size > max_number:
                item = _get_equally_spaced(item, max_number)
            return _serialize(item.tolist(), max_number)
    except ImportError:
        pass

    if isinstance(item, (float, int)):
        return round(float(item), 5)

    raise TypeError(f"Type '{type(item)}' not supported by _serialize")


@pytest.fixture
def files_path():
    """Path to the fixture files used for the tests."""
    return Path(__file__).parent / "outputs" / "fixtures"


@pytest.fixture()
def json_serializer():
    """Make a dictionary JSON-serializable for regression testing.

    Rounds floats to 5 digits and converts numpy arrays to lists.
    """

    def factory(data):
        return _serialize(data)

    return factory


@pytest.fixture()
def custom_serializer():
    """Like `json_serializer`, but subsamples large arrays to `max_number` elements.

    Usage::

        custom_serializer(data, max_number=50)
    """

    def factory(data, max_number=None):
        return _serialize(data, max_number=max_number)

    return factory


@pytest.fixture()
def robust_data_regression_check(data_regression, json_serializer):
    """Run `data_regression.check` after making the data JSON-serializable."""

    def factory(data):
        return data_regression.check(json_serializer(data))

    return factory
