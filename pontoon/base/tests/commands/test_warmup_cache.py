"""
PoC: Mutable default argument bug in warmup_cache.py Command.warmup_url().

Before the fix, the method signature was:
    def warmup_url(self, url, keys=[], is_ajax=False)

This is a classic Python mutable default argument bug. The default list `[]`
is created once at class definition time and shared across all method calls.
If the `keys` list is ever mutated (e.g. via .append()), subsequent calls
that rely on the default will see the mutated version — leading to unexpected
cache key deletions.

The fix changed `keys=[]` to `keys=None` with `for key in keys or []:` in
the method body, ensuring each call handles the absence of keys safely.
"""

from unittest.mock import MagicMock, patch

from pontoon.base.management.commands.warmup_cache import Command


def test_warmup_url_default_keys_is_not_shared():
    """PoC: Verify the default `keys` parameter is not a shared mutable list.

    Before the fix, calling warmup_url without `keys` would reuse the same
    list object. If any code mutated that list, subsequent calls would see
    stale keys from previous invocations.

    After the fix, keys defaults to None, and the method body handles it
    safely with `for key in keys or []:`.
    """
    cmd = Command()

    # Check the method's defaults using introspection
    # Before fix: warmup_url.__defaults__ = ([], False)
    # After fix: warmup_url.__defaults__ = (None, False)
    defaults = cmd.warmup_url.__func__.__defaults__
    assert defaults is not None

    # The first default (keys) should be None, not []
    keys_default = defaults[0]
    assert keys_default is None, (
        f"keys parameter default should be None, not {keys_default!r}. "
        "This indicates the mutable default argument bug is still present."
    )


@patch("pontoon.base.management.commands.warmup_cache.requests")
@patch("pontoon.base.management.commands.warmup_cache.cache")
def test_warmup_url_no_keys_doesnt_delete_cache(mock_cache, mock_requests):
    """PoC: Calling warmup_url without keys should not call cache.delete().

    This verifies that when no keys are passed, the method doesn't attempt
    to iterate over an unexpectedly populated default list.
    """
    cmd = Command()
    cmd.stdout = MagicMock()

    cmd.warmup_url("http://example.com/test")

    # cache.delete should never be called when no keys are provided
    mock_cache.delete.assert_not_called()
    # But the request should still be made
    mock_requests.get.assert_called_once()


@patch("pontoon.base.management.commands.warmup_cache.requests")
@patch("pontoon.base.management.commands.warmup_cache.cache")
def test_warmup_url_with_explicit_keys_deletes_cache(mock_cache, mock_requests):
    """PoC: Calling warmup_url with explicit keys should delete them."""
    cmd = Command()
    cmd.stdout = MagicMock()

    cmd.warmup_url("http://example.com/test", keys=["key1", "key2"])

    assert mock_cache.delete.call_count == 2
    mock_cache.delete.assert_any_call("key1")
    mock_cache.delete.assert_any_call("key2")


@patch("pontoon.base.management.commands.warmup_cache.requests")
@patch("pontoon.base.management.commands.warmup_cache.cache")
def test_warmup_url_default_keys_isolation_across_calls(mock_cache, mock_requests):
    """PoC: Multiple calls without keys should each get independent defaults.

    Before the fix, if the default list were ever mutated (by some other code
    path or a future change), the mutation would persist across calls. This
    test verifies calls are isolated.
    """
    cmd = Command()
    cmd.stdout = MagicMock()

    # First call: no keys
    cmd.warmup_url("http://example.com/first")
    assert mock_cache.delete.call_count == 0

    # Second call: explicit keys
    cmd.warmup_url("http://example.com/second", keys=["cache_key"])
    assert mock_cache.delete.call_count == 1

    mock_cache.delete.reset_mock()

    # Third call: no keys again — should still not delete anything
    # (Before fix, if the default list were mutated, this would fail)
    cmd.warmup_url("http://example.com/third")
    assert mock_cache.delete.call_count == 0
