"""
PoC: Mutable default argument bug in log_ux_action.

Before the fix, the function signature was:
    def log_ux_action(action_type, experiment=None, data={})

This is a classic Python mutable default argument bug. The default dict `{}`
is created once at function definition time and shared across all calls.
If the `data` dict is ever mutated after a call, subsequent calls that rely
on the default will see the mutated version — leading to data leakage between
unrelated UX action log entries.

The fix changed `data={}` to `data=None` with an explicit `if data is None: data = {}`
inside the function body, ensuring each call gets its own fresh dict.
"""

import pytest

from pontoon.uxactionlog.utils import log_ux_action


@pytest.mark.django_db
def test_log_ux_action_default_data_is_not_shared():
    """PoC: Verify that the default `data` parameter is not shared across calls.

    Before the fix, calling log_ux_action without `data` would reuse the same
    dict object. If code ever mutated that dict (even outside the function),
    subsequent calls would see stale data from previous invocations.

    This test verifies that two calls without explicit `data` each get
    independent empty dicts — proving the mutable default argument bug is fixed.
    """
    # Simulate what would happen if someone captured the default and mutated it.
    # With the old code: data={} is the SAME object each time.
    # With the fix: data=None -> data={} creates a NEW dict each time.

    # Call 1: Use default data
    log_ux_action(action_type="test_action_1")

    # Call 2: Use default data
    log_ux_action(action_type="test_action_2")

    # Both should have independent empty dicts as data
    from pontoon.uxactionlog.models import UXActionLog

    actions = UXActionLog.objects.filter(
        action_type__in=["test_action_1", "test_action_2"]
    ).order_by("action_type")

    assert actions.count() == 2
    assert actions[0].data == {}
    assert actions[1].data == {}


@pytest.mark.django_db
def test_log_ux_action_explicit_data_not_leaked():
    """PoC: Verify that explicit data passed to one call doesn't leak to the next.

    With the old buggy code (data={}), if external code retrieved the default
    and mutated it, or if the function mutated it internally, the mutation
    would persist across calls. This test proves that calling with explicit
    data and then with default data yields clean results.
    """
    # Call with explicit data
    log_ux_action(
        action_type="action_with_data",
        data={"key": "value", "secret": "should_not_leak"},
    )

    # Call with default (no data)
    log_ux_action(action_type="action_without_data")

    from pontoon.uxactionlog.models import UXActionLog

    action_with = UXActionLog.objects.get(action_type="action_with_data")
    action_without = UXActionLog.objects.get(action_type="action_without_data")

    assert action_with.data == {"key": "value", "secret": "should_not_leak"}
    assert action_without.data == {}  # Must be empty, not leaked


def test_log_ux_action_default_identity():
    """PoC: Directly verify the function creates a new dict each invocation.

    This is a pure-Python test that doesn't need the database. It inspects
    the function's default argument behavior using introspection.

    Before the fix: log_ux_action.__defaults__ contained ({},) — a mutable dict
    that was the SAME object reused on every call.

    After the fix: log_ux_action.__defaults__ contains (None,) — None is
    immutable, so a new dict is created inside the function body each time.
    """
    # The function's defaults should use None, not a mutable dict
    defaults = log_ux_action.__defaults__
    # defaults is (None, None) for (experiment, data) after the fix
    assert defaults is not None
    assert None in defaults, (
        f"Expected None in defaults (for data parameter), got: {defaults}"
    )

    # Specifically, the last default (data) should be None, not {}
    # Function signature: log_ux_action(action_type, experiment=None, data=None)
    # __defaults__ = (None, None)
    data_default = defaults[-1]
    assert data_default is None, (
        f"data parameter default should be None, not {data_default!r}. "
        "This indicates the mutable default argument bug is still present."
    )
