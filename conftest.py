"""Auto-apply the ``fast`` marker to every test that is not explicitly ``slow``.

This gives the iteration path a positive name (``-m fast``) and makes any newly
written, unmarked test fast-by-default.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("slow") is None:
            item.add_marker(pytest.mark.fast)
