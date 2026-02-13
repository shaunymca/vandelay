"""Tests for the rule-based message complexity classifier."""

from __future__ import annotations

import pytest

from vandelay.routing.classifier import classify


class TestSimpleClassification:
    """Messages that should be classified as 'simple'."""

    @pytest.mark.parametrize("message", [
        "what time is it?",
        "What time is it",
        "hello",
        "Hi",
        "thanks",
        "ok",
        "yes",
        "who are you?",
        "what can you do?",
        "good morning",
        "tell me a joke",
        "",
    ])
    def test_simple_messages(self, message: str):
        assert classify(message) == "simple"

    def test_short_factual_question(self):
        assert classify("what is 2+2?") == "simple"

    def test_short_who_question(self):
        assert classify("who is the president?") == "simple"


class TestComplexClassification:
    """Messages that should be classified as 'complex'."""

    @pytest.mark.parametrize("message", [
        "analyze this codebase and refactor the authentication module",
        "implement a new feature that handles user registration with email verification",
        "debug the issue where the database connection drops after 30 seconds",
        "write a Python function that calculates the Levenshtein distance between two strings",
        "create a REST API endpoint that handles file uploads with validation",
    ])
    def test_complex_messages(self, message: str):
        assert classify(message) == "complex"

    def test_long_message_is_complex(self):
        long_msg = "Please help me with " + "this task " * 30
        assert classify(long_msg) == "complex"

    def test_code_content_is_complex(self):
        msg = "I'm getting this error in my code:\n```\nTraceback...\n```"
        assert classify(msg) == "complex"

    def test_multi_step_is_complex(self):
        msg = "First, check the logs, and then restart the service"
        assert classify(msg) == "complex"

    def test_numbered_list_is_complex(self):
        msg = "I need you to:\n1. Check the database\n2. Fix the migration\n3. Deploy"
        assert classify(msg) == "complex"


class TestEdgeCases:
    def test_empty_string(self):
        assert classify("") == "simple"

    def test_whitespace_only(self):
        assert classify("   ") == "simple"

    def test_returns_string(self):
        result = classify("hello")
        assert isinstance(result, str)
        assert result in ("simple", "complex")
