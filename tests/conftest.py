"""Project-wide pytest fixtures & hooks.

Docs: https://docs.pytest.org/en/stable/how-to/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

Load the `dough.testing` plugin explicitly so `json_serializer` and
`robust_data_regression_check` are available to the test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ["dough.testing.plugin"]


@pytest.fixture
def files_path():
    """Path to the fixture files used for the tests."""
    return Path(__file__).parent / "outputs" / "fixtures"
