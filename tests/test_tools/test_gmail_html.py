"""Tests for Gmail HTML body fallback."""

from __future__ import annotations

import base64

from vandelay.tools.manager import _fix_gmail_html_body


class _FakeGmailTool:
    """Minimal stand-in for Agno GmailTools."""

    def _get_message_body(self, msg_data: dict) -> str:
        """Default: only reads text/plain — ignores HTML."""
        body = ""
        attachments = []
        try:
            if "parts" in msg_data["payload"]:
                for part in msg_data["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode()
                    elif "filename" in part and part["filename"]:
                        attachments.append(part["filename"])
        except Exception:
            return "Unable to decode message body"

        if attachments:
            return f"{body}\n\nAttachments: {', '.join(attachments)}"
        return body


def _encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _make_msg(plain: str = "", html: str = "", attachments: list | None = None):
    """Build a minimal Gmail message payload."""
    parts = []
    if plain:
        parts.append({
            "mimeType": "text/plain",
            "body": {"data": _encode(plain)},
        })
    else:
        # Empty plain text part (common in forwarded emails)
        parts.append({
            "mimeType": "text/plain",
            "body": {"data": _encode("")},
        })
    if html:
        parts.append({
            "mimeType": "text/html",
            "body": {"data": _encode(html)},
        })
    if attachments:
        for name in attachments:
            parts.append({
                "mimeType": "image/png",
                "filename": name,
                "body": {"attachmentId": "fake"},
            })
    return {"payload": {"parts": parts}}


def test_plain_text_passes_through():
    """When plain text exists, HTML fallback should not be triggered."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    msg = _make_msg(plain="Hello, this is a normal email.")
    result = fake._get_message_body(msg)
    assert result == "Hello, this is a normal email."


def test_html_fallback_when_plain_empty():
    """When plain text is empty, should extract text from HTML body."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    html = "<div><p>Hi Shaun,</p><p>Here is the forwarded thread.</p></div>"
    msg = _make_msg(plain="", html=html)
    result = fake._get_message_body(msg)
    assert "Hi Shaun" in result
    assert "forwarded thread" in result
    assert "<div>" not in result  # Tags should be stripped


def test_html_fallback_strips_style_and_script():
    """HTML fallback should strip style/script tags."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    html = (
        "<style>.foo { color: red; }</style>"
        "<script>alert('xss')</script>"
        "<p>Important content here.</p>"
    )
    msg = _make_msg(plain="", html=html)
    result = fake._get_message_body(msg)
    assert "Important content" in result
    assert "color: red" not in result
    assert "alert" not in result


def test_html_fallback_preserves_attachments():
    """HTML fallback should preserve attachment list from original result."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    html = "<p>Email thread content.</p>"
    msg = _make_msg(plain="", html=html, attachments=["image001.png", "image002.png"])
    result = fake._get_message_body(msg)
    assert "Email thread content" in result
    assert "image001.png" in result
    assert "image002.png" in result


def test_no_html_returns_original():
    """When neither plain nor HTML has content, return original result."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    msg = _make_msg(plain="", html="")
    result = fake._get_message_body(msg)
    assert result == "" or result.strip() == ""


def test_nested_multipart_html():
    """Should find HTML in nested multipart/alternative parts."""
    fake = _FakeGmailTool()
    _fix_gmail_html_body(fake)

    msg = {
        "payload": {
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _encode("")}},
                        {
                            "mimeType": "text/html",
                            "body": {"data": _encode("<p>Nested HTML content.</p>")},
                        },
                    ],
                },
            ],
        },
    }
    result = fake._get_message_body(msg)
    assert "Nested HTML content" in result
