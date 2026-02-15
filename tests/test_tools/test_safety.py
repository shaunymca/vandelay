"""Tests for the safety guard on shell tools."""

from __future__ import annotations

import pytest

from vandelay.tools.safety import SafeShellTools


@pytest.fixture
def safe_shell() -> SafeShellTools:
    """SafeShellTools in tiered mode."""
    return SafeShellTools(
        mode="tiered",
        allowed_commands=["ls", "cat", "echo", "git status"],
        blocked_patterns=["rm -rf /", "mkfs", "dd if="],
        timeout=10,
    )


@pytest.fixture
def trust_shell() -> SafeShellTools:
    return SafeShellTools(mode="trust", timeout=10)


@pytest.fixture
def confirm_shell() -> SafeShellTools:
    return SafeShellTools(mode="confirm", timeout=10)


def test_blocked_pattern_always_blocked(safe_shell: SafeShellTools):
    """Dangerous commands should be blocked in every mode."""
    result = safe_shell.run_command("rm -rf /")
    assert "BLOCKED" in result


def test_blocked_even_in_trust_mode(trust_shell: SafeShellTools):
    """Blocked patterns should apply even in trust mode."""
    trust_shell.blocked_patterns = ["rm -rf /"]
    result = trust_shell.run_command("rm -rf /")
    assert "BLOCKED" in result


def test_tiered_allows_safe_command(safe_shell: SafeShellTools):
    """Safe commands should execute in tiered mode."""
    result = safe_shell.run_command("echo hello")
    assert "hello" in result


def test_tiered_blocks_unsafe_command(safe_shell: SafeShellTools):
    """Unsafe commands should need approval in tiered mode."""
    result = safe_shell.run_command("curl http://example.com")
    assert "NEEDS APPROVAL" in result


def test_tiered_allows_exact_match(safe_shell: SafeShellTools):
    """Exact command match (no args) should work."""
    result = safe_shell.run_command("ls")
    # ls should produce some output or "(no output)"
    assert "NEEDS APPROVAL" not in result
    assert "BLOCKED" not in result


def test_confirm_mode_executes(confirm_shell: SafeShellTools):
    """Confirm mode should execute and note it."""
    result = confirm_shell.run_command("echo test")
    assert "[confirm mode]" in result
    assert "test" in result


def test_trust_mode_executes(trust_shell: SafeShellTools):
    """Trust mode should execute directly."""
    result = trust_shell.run_command("echo trusted")
    assert "trusted" in result
    assert "[confirm mode]" not in result


def test_check_safety_blocked(safe_shell: SafeShellTools):
    """check_safety should report blocked commands."""
    result = safe_shell.check_safety("dd if=/dev/zero")
    assert "BLOCKED" in result


def test_check_safety_allowed_tiered(safe_shell: SafeShellTools):
    """check_safety should report safe commands in tiered mode."""
    result = safe_shell.check_safety("echo hello")
    assert "ALLOWED" in result


def test_check_safety_needs_approval(safe_shell: SafeShellTools):
    """check_safety should report risky commands need approval."""
    result = safe_shell.check_safety("wget http://example.com")
    assert "NEEDS APPROVAL" in result


def test_default_blocks_source_code_paths():
    """Default blocked_patterns should prevent writes to src/vandelay."""
    from vandelay.config.models import SafetyConfig

    defaults = SafetyConfig()
    shell = SafeShellTools(
        mode="trust",
        blocked_patterns=defaults.blocked_patterns,
        timeout=10,
    )
    # Unix-style path
    result = shell.run_command("sed -i 's/foo/bar/' src/vandelay/tools/manager.py")
    assert "BLOCKED" in result
    # Windows-style path
    result = shell.run_command("echo bad > src\\vandelay\\tools\\manager.py")
    assert "BLOCKED" in result
    # Should not block unrelated commands
    result = shell.check_safety("echo hello")
    assert "BLOCKED" not in result


def test_find_auto_excludes_noise_dirs():
    """find commands should get exclusion patterns for noise directories."""
    shell = SafeShellTools(mode="trust", timeout=10)
    processed = shell._preprocess_command('find . -name "*.py"')
    assert '-not -path "*/.venv/*"' in processed
    assert '-not -path "*/.cache/*"' in processed
    assert '-not -path "*/node_modules/*"' in processed
    assert '-not -path "*/__pycache__/*"' in processed
    assert '-not -path "*/.git/*"' in processed
    # Original command preserved at the start
    assert processed.startswith('find . -name "*.py"')


def test_find_preserves_explicit_prune():
    """find with -prune should be left unchanged."""
    shell = SafeShellTools(mode="trust", timeout=10)
    cmd = 'find . -prune -name "*.py"'
    assert shell._preprocess_command(cmd) == cmd


def test_grep_recursive_auto_excludes():
    """grep -r commands should get --exclude-dir patterns."""
    shell = SafeShellTools(mode="trust", timeout=10)
    processed = shell._preprocess_command("grep -r foo .")
    assert "--exclude-dir=.venv" in processed
    assert "--exclude-dir=node_modules" in processed
    assert "--exclude-dir=__pycache__" in processed
    assert processed.startswith("grep -r foo .")


def test_grep_R_auto_excludes():
    """grep -R should also get exclusions."""
    shell = SafeShellTools(mode="trust", timeout=10)
    processed = shell._preprocess_command("grep -R pattern src/")
    assert "--exclude-dir=.venv" in processed


def test_grep_recursive_preserves_explicit_exclude():
    """grep with --exclude-dir should be left unchanged."""
    shell = SafeShellTools(mode="trust", timeout=10)
    cmd = "grep -r --exclude-dir=.git foo ."
    assert shell._preprocess_command(cmd) == cmd


def test_grep_non_recursive_unchanged():
    """Non-recursive grep should pass through untouched."""
    shell = SafeShellTools(mode="trust", timeout=10)
    assert shell._preprocess_command("grep foo bar.txt") == "grep foo bar.txt"


def test_non_find_commands_unchanged():
    """Non-find/grep commands should pass through untouched."""
    shell = SafeShellTools(mode="trust", timeout=10)
    assert shell._preprocess_command("ls -la") == "ls -la"
    assert shell._preprocess_command("echo find me") == "echo find me"


def test_command_timeout():
    """Commands that exceed timeout should fail gracefully."""
    shell = SafeShellTools(mode="trust", timeout=1)
    # Use a command that sleeps — platform-dependent
    import sys
    if sys.platform == "win32":
        result = shell.run_command("ping -n 5 127.0.0.1")
    else:
        result = shell.run_command("sleep 5")
    assert "timed out" in result.lower() or "timeout" in result.lower()
