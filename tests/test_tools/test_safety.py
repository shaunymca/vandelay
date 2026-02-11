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
