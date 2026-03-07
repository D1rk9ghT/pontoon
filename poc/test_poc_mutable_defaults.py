"""
Standalone PoC tests for the mutable default argument bugs.

These tests can run without Django installed. They test the bug pattern
directly rather than relying on Django's ORM.

Run: python -m pytest poc/test_poc_mutable_defaults.py -v
"""

import pytest


class TestMutableDefaultDict:
    """PoC for data={} bug in pontoon/uxactionlog/utils.py"""

    def test_buggy_pattern_shares_default_dict(self):
        """Demonstrate the bug: default dict is shared across calls."""

        def buggy_function(data={}):
            return data

        result1 = buggy_function()
        result2 = buggy_function()

        # BUG: Same object returned
        assert result1 is result2, "Expected same object (demonstrating the bug)"

        # Mutation leaks
        result1["leaked"] = True
        result3 = buggy_function()
        assert "leaked" in result3, "Expected data leakage (demonstrating the bug)"

    def test_fixed_pattern_creates_new_dict_each_call(self):
        """Demonstrate the fix: None default creates new dict each call."""

        def fixed_function(data=None):
            if data is None:
                data = {}
            return data

        result1 = fixed_function()
        result2 = fixed_function()

        # FIX: Different objects
        assert result1 is not result2, "Expected different objects (fix working)"

        # No mutation leakage
        result1["leaked"] = True
        result3 = fixed_function()
        assert "leaked" not in result3, "Expected no data leakage (fix working)"

    def test_actual_code_uses_none_default(self):
        """Verify the actual log_ux_action function uses None as default."""
        # Import the function module directly to inspect its defaults
        import importlib.util
        import os

        spec = importlib.util.spec_from_file_location(
            "utils",
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "pontoon",
                "uxactionlog",
                "utils.py",
            ),
        )
        # We can't actually import it (needs Django), but we can read the source
        source_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pontoon",
            "uxactionlog",
            "utils.py",
        )
        with open(source_path) as f:
            source = f.read()

        # Verify the fix is in place
        assert "data=None" in source, "Expected data=None in source (fix applied)"
        assert "data={}" not in source, "Should not have data={} (bug would be present)"
        assert "if data is None:" in source, "Expected None check in source"


class TestMutableDefaultList:
    """PoC for keys=[] bug in pontoon/base/management/commands/warmup_cache.py"""

    def test_buggy_pattern_shares_default_list(self):
        """Demonstrate the bug: default list is shared across calls."""

        def buggy_function(keys=[]):
            for key in keys:
                pass
            return keys

        result1 = buggy_function()
        result2 = buggy_function()

        # BUG: Same object returned
        assert result1 is result2, "Expected same object (demonstrating the bug)"

        # Mutation leaks
        result1.append("unexpected_key")
        result3 = buggy_function()
        assert "unexpected_key" in result3, (
            "Expected key leakage (demonstrating the bug)"
        )

    def test_fixed_pattern_uses_none_default(self):
        """Demonstrate the fix: None default prevents list sharing."""

        def fixed_function(keys=None):
            for key in keys or []:
                pass
            return keys

        result1 = fixed_function()
        result2 = fixed_function()

        # FIX: Both return None (no mutable object)
        assert result1 is None
        assert result2 is None

        # Explicit keys work
        result3 = fixed_function(keys=["key1"])
        assert result3 == ["key1"]

        # Back to default: still None
        result4 = fixed_function()
        assert result4 is None

    def test_actual_code_uses_none_default(self):
        """Verify the actual warmup_cache.py uses None as default."""
        import os

        source_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "pontoon",
            "base",
            "management",
            "commands",
            "warmup_cache.py",
        )
        with open(source_path) as f:
            source = f.read()

        # Verify the fix is in place
        assert "keys=None" in source, "Expected keys=None in source (fix applied)"
        assert "keys=[]" not in source, "Should not have keys=[] (bug would be present)"
        assert "keys or []" in source, "Expected 'keys or []' pattern in source"


class TestDockerfileFixes:
    """PoC for Dockerfile and workflow fixes."""

    def test_dockerfile_has_noinput_flag(self):
        """Verify docker/Dockerfile uses --noinput with collectstatic."""
        import os

        dockerfile_path = os.path.join(
            os.path.dirname(__file__), "..", "docker", "Dockerfile"
        )
        with open(dockerfile_path) as f:
            content = f.read()

        assert "collectstatic --noinput" in content, (
            "docker/Dockerfile should use 'collectstatic --noinput'"
        )

    def test_workflow_has_noinput_flag(self):
        """Verify backend.yml workflow uses --noinput with collectstatic."""
        import os

        workflow_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            ".github",
            "workflows",
            "backend.yml",
        )
        with open(workflow_path) as f:
            content = f.read()

        assert "collectstatic --noinput" in content, (
            "backend.yml should use 'collectstatic --noinput'"
        )

    def test_dockerfile_mozcloud_uses_shell_form_cmd(self):
        """Verify Dockerfile-mozcloud uses shell form for CMD.

        Docker's exec form (JSON array) does NOT invoke a shell, so
        environment variable references like ${GUNICORN_WORKERS:-4}
        are passed as literal strings. The fix wraps the command in
        'sh -c' to enable shell variable expansion.
        """
        import os

        dockerfile_path = os.path.join(
            os.path.dirname(__file__), "..", "docker", "Dockerfile-mozcloud"
        )
        with open(dockerfile_path) as f:
            content = f.read()

        # Should use sh -c for shell expansion
        assert '"sh", "-c"' in content, (
            "Dockerfile-mozcloud should use 'sh -c' for shell variable expansion"
        )

        # Should NOT have the buggy exec-form with literal variable
        # (The old pattern was: CMD ["gunicorn", ..., "--workers", "${GUNICORN_WORKERS:-4}", ...])
        lines = content.strip().split("\n")
        # Get the CMD line
        cmd_line = ""
        for line in lines:
            if line.startswith("CMD"):
                cmd_line = line
                break

        assert cmd_line, "Should have a CMD instruction"
        assert "exec gunicorn" in cmd_line, (
            "Should use 'exec' for proper signal forwarding"
        )

    def test_shell_variable_expansion_works(self):
        """Verify that shell form correctly expands variables."""
        import subprocess

        # Test default value expansion
        result = subprocess.run(
            ["sh", "-c", "echo ${GUNICORN_WORKERS:-4}"],
            capture_output=True,
            text=True,
            env={},  # No GUNICORN_WORKERS set
        )
        assert result.stdout.strip() == "4", (
            f"Default expansion failed: got '{result.stdout.strip()}'"
        )

        # Test custom value expansion
        result = subprocess.run(
            ["sh", "-c", "echo ${GUNICORN_WORKERS:-4}"],
            capture_output=True,
            text=True,
            env={"GUNICORN_WORKERS": "8"},
        )
        assert result.stdout.strip() == "8", (
            f"Custom expansion failed: got '{result.stdout.strip()}'"
        )

    def test_exec_form_does_not_expand_variables(self):
        """Demonstrate that exec form passes literal strings (the bug)."""
        import subprocess

        # Simulate exec form: pass the variable reference as a literal argument
        # In Docker exec form, this string would NOT be expanded
        literal = "${GUNICORN_WORKERS:-4}"

        # In a shell, you can see this is just a string
        result = subprocess.run(
            ["echo", literal],  # exec form: no shell
            capture_output=True,
            text=True,
        )
        # echo with exec form just outputs the literal string
        assert "${GUNICORN_WORKERS" in result.stdout, (
            "Exec form should pass literal string without expansion"
        )
