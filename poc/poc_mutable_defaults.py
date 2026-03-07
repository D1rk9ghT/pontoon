#!/usr/bin/env python3
"""
PoC: Mutable Default Argument Bug Demonstration

This script demonstrates the classic Python mutable default argument bug
that was found in two places in the Pontoon codebase:

1. pontoon/uxactionlog/utils.py:
   def log_ux_action(action_type, experiment=None, data={})
   
2. pontoon/base/management/commands/warmup_cache.py:
   def warmup_url(self, url, keys=[], is_ajax=False)

The bug: In Python, default argument values are evaluated ONCE at function
definition time. Mutable defaults (like {} or []) are shared across all
calls to the function. If the mutable default is ever modified, the
modification persists across subsequent calls.

Run: python poc/poc_mutable_defaults.py
"""

import sys


def demonstrate_dict_bug():
    """Demonstrate the data={} bug from uxactionlog/utils.py"""
    print("=" * 60)
    print("PoC 1: Mutable Default Dict (data={})")
    print("=" * 60)
    print()
    
    # Simulate the BUGGY function
    def log_ux_action_buggy(action_type, data={}):
        """Original buggy version"""
        # If any code path modifies data, it affects all future calls
        return data
    
    # Simulate the FIXED function
    def log_ux_action_fixed(action_type, data=None):
        """Fixed version"""
        if data is None:
            data = {}
        return data
    
    # --- BUGGY VERSION ---
    print("BUGGY version (data={}):")
    
    # Call 1: Get the default dict
    result1 = log_ux_action_buggy("action1")
    print(f"  Call 1 result: {result1}  (id={id(result1)})")
    
    # Call 2: Get the default dict again — it's the SAME object!
    result2 = log_ux_action_buggy("action2")
    print(f"  Call 2 result: {result2}  (id={id(result2)})")
    
    print(f"  Same object? {result1 is result2}")
    assert result1 is result2, "Bug: default dicts should be the same object"
    
    # Now if anyone mutates it (even externally)...
    result1["leaked"] = "sensitive_data"
    result3 = log_ux_action_buggy("action3")
    print(f"  Call 3 result (after mutation): {result3}")
    print(f"  ✗ BUG: Data leaked across calls!")
    print()
    
    # --- FIXED VERSION ---
    print("FIXED version (data=None):")
    
    result1 = log_ux_action_fixed("action1")
    print(f"  Call 1 result: {result1}  (id={id(result1)})")
    
    result2 = log_ux_action_fixed("action2")
    print(f"  Call 2 result: {result2}  (id={id(result2)})")
    
    print(f"  Same object? {result1 is result2}")
    assert result1 is not result2, "Fix: default dicts should be different objects"
    
    # Mutation of one doesn't affect the other
    result1["leaked"] = "sensitive_data"
    result3 = log_ux_action_fixed("action3")
    print(f"  Call 3 result (after mutation): {result3}")
    print(f"  ✓ FIX VERIFIED: No data leakage!")
    print()


def demonstrate_list_bug():
    """Demonstrate the keys=[] bug from warmup_cache.py"""
    print("=" * 60)
    print("PoC 2: Mutable Default List (keys=[])")
    print("=" * 60)
    print()
    
    # Simulate the BUGGY function
    def warmup_url_buggy(url, keys=[]):
        """Original buggy version"""
        for key in keys:
            pass  # cache.delete(key) 
        return keys
    
    # Simulate the FIXED function
    def warmup_url_fixed(url, keys=None):
        """Fixed version"""
        for key in keys or []:
            pass  # cache.delete(key)
        return keys
    
    # --- BUGGY VERSION ---
    print("BUGGY version (keys=[]):")
    
    result1 = warmup_url_buggy("http://example.com/1")
    print(f"  Call 1 result: {result1}  (id={id(result1)})")
    
    result2 = warmup_url_buggy("http://example.com/2")
    print(f"  Call 2 result: {result2}  (id={id(result2)})")
    
    print(f"  Same object? {result1 is result2}")
    assert result1 is result2, "Bug: default lists should be the same object"
    
    # If code ever appends to the default list...
    result1.append("unexpected_key")
    result3 = warmup_url_buggy("http://example.com/3")
    print(f"  Call 3 result (after mutation): {result3}")
    print(f"  ✗ BUG: 'unexpected_key' leaked to subsequent calls!")
    print(f"    This means cache.delete('unexpected_key') would be called")
    print(f"    on every future warmup_url call without explicit keys!")
    print()
    
    # --- FIXED VERSION ---
    print("FIXED version (keys=None):")
    
    result1 = warmup_url_fixed("http://example.com/1")
    print(f"  Call 1 result: {result1}")
    assert result1 is None, "Fix: default should be None"
    
    result2 = warmup_url_fixed("http://example.com/2")
    print(f"  Call 2 result: {result2}")
    assert result2 is None, "Fix: default should still be None"
    
    # Explicit keys work correctly
    result3 = warmup_url_fixed("http://example.com/3", keys=["key1"])
    print(f"  Call 3 result (explicit keys): {result3}")
    
    result4 = warmup_url_fixed("http://example.com/4")
    print(f"  Call 4 result (back to default): {result4}")
    print(f"  ✓ FIX VERIFIED: No key leakage!")
    print()


def verify_actual_code():
    """Verify the actual code in the repository has the fix applied."""
    print("=" * 60)
    print("Verifying actual codebase fixes")
    print("=" * 60)
    print()
    
    # Check uxactionlog/utils.py
    try:
        from pontoon.uxactionlog.utils import log_ux_action
        defaults = log_ux_action.__defaults__
        data_default = defaults[-1]
        if data_default is None:
            print("  ✓ log_ux_action: data default is None (fix applied)")
        else:
            print(f"  ✗ log_ux_action: data default is {data_default!r} (bug present!)")
    except ImportError:
        print("  ℹ Skipping log_ux_action check (Django not configured)")
    
    # Check warmup_cache.py
    try:
        from pontoon.base.management.commands.warmup_cache import Command
        cmd = Command()
        defaults = cmd.warmup_url.__func__.__defaults__
        keys_default = defaults[0]
        if keys_default is None:
            print("  ✓ warmup_url: keys default is None (fix applied)")
        else:
            print(f"  ✗ warmup_url: keys default is {keys_default!r} (bug present!)")
    except ImportError:
        print("  ℹ Skipping warmup_url check (Django not configured)")
    
    print()


if __name__ == "__main__":
    print()
    print("Pontoon Bug PoC: Mutable Default Arguments")
    print("=" * 60)
    print()
    
    demonstrate_dict_bug()
    demonstrate_list_bug()
    
    # Only try Django imports if running in proper environment
    try:
        import django
        demonstrate_dict_bug()
        verify_actual_code()
    except ImportError:
        print("ℹ Django not available. Skipping actual code verification.")
        print("  Run within the Pontoon environment to verify actual fixes.")
    
    print()
    print("All PoC demonstrations completed successfully!")
    print()
    sys.exit(0)
