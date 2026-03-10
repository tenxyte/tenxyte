"""
Pure unit tests for tenxyte.core (no Django dependencies).

Run these tests with:
    pytest tests/core/ -p no:django

These tests verify Core services work with mock adapters,
ensuring framework-agnostic behavior.
"""

import pytest

# Mark all tests in this directory as pure Core tests (no Django)
pytestmark = [
    pytest.mark.no_django,
]
