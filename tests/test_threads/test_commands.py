"""Tests for /thread and /threads command parsing."""

from vandelay.threads.commands import parse_thread_command


def test_parse_thread_switch():
    cmd = parse_thread_command("/thread project-a")
    assert cmd.action == "switch"
    assert cmd.thread_name == "project-a"


def test_parse_thread_switch_with_spaces():
    cmd = parse_thread_command("/thread my cool project")
    assert cmd.action == "switch"
    assert cmd.thread_name == "my cool project"


def test_parse_thread_show_current():
    cmd = parse_thread_command("/thread")
    assert cmd.action == "show_current"


def test_parse_thread_show_current_whitespace_only():
    cmd = parse_thread_command("/thread   ")
    assert cmd.action == "show_current"


def test_parse_threads_list():
    cmd = parse_thread_command("/threads")
    assert cmd.action == "list"


def test_parse_normal_message():
    cmd = parse_thread_command("hello world")
    assert cmd.action == "none"


def test_parse_thread_in_sentence():
    """Messages containing /thread mid-sentence should not trigger."""
    cmd = parse_thread_command("can you explain /thread?")
    assert cmd.action == "none"
