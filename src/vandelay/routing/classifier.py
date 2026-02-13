"""Rule-based message complexity classifier.

Classifies messages into "simple" or "complex" without any LLM call.
Designed for <1ms execution — pure string heuristics.
"""

from __future__ import annotations

import re

# Short, factual question starters → simple
_SIMPLE_PATTERNS = re.compile(
    r"^(what time|what date|what day|what is the weather|what's the weather|"
    r"hi|hello|hey|thanks|thank you|ok|okay|yes|no|sure|"
    r"who are you|what can you do|what's your name|"
    r"remind me|set a timer|set a reminder|"
    r"tell me a joke|good morning|good night)[\s?!.,]*$",
    re.IGNORECASE,
)

# Indicators of complex / multi-step tasks
_COMPLEX_KEYWORDS = [
    "analyze", "refactor", "implement", "debug", "investigate",
    "compare", "evaluate", "design", "architect", "optimize",
    "explain in detail", "step by step", "write a", "create a",
    "build a", "set up", "configure", "deploy", "migrate",
    "review this", "audit", "summarize the", "research",
]

# Technical markers that push toward complex
_TECHNICAL_MARKERS = [
    "```", "code", "function", "class ", "error", "traceback",
    "exception", "bug", "api", "database", "query", "sql",
    "docker", "kubernetes", "ci/cd", "pipeline",
]


def classify(message: str) -> str:
    """Classify a user message as "simple" or "complex".

    Uses a rule-based scoring system:
    - Message length
    - Question type keywords
    - Code/technical markers
    - Multi-step indicators

    Returns:
        "simple" or "complex"
    """
    text = message.strip()

    if not text:
        return "simple"

    # Quick check: if it matches a known simple pattern exactly, it's simple
    if _SIMPLE_PATTERNS.match(text):
        return "simple"

    score = 0
    lower = text.lower()

    # Length scoring
    if len(text) > 200:
        score += 1
    if len(text) > 500:
        score += 1

    # Complex keyword scoring
    for keyword in _COMPLEX_KEYWORDS:
        if keyword in lower:
            score += 1
            break  # one match is enough

    # Technical markers
    for marker in _TECHNICAL_MARKERS:
        if marker in lower:
            score += 1
            break

    # Multi-step indicators (numbered lists, bullet points, "and then", "also")
    if re.search(r"\b(and then|also|additionally|furthermore|first.*then)\b", lower):
        score += 1
    if re.search(r"^\s*[\d]+[.)]\s", text, re.MULTILINE):
        score += 1

    # Question word at start with very short message → likely simple
    if len(text) < 60 and re.match(r"^(what|when|where|who|how much|how many)\b", lower):
        score -= 1

    return "complex" if score >= 1 else "simple"
