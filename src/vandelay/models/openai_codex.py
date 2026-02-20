"""Custom Agno model that calls chatgpt.com/backend-api/codex/responses.

Uses ChatGPT Plus/Pro OAuth credentials from ~/.codex/auth.json — the same
token written by `codex login` (the @openai/codex CLI). No API key billing.

Implements the Agno Model abstract interface so it can be dropped in wherever
Agno expects a Model, including as the main agent model or a team member model.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from agno.models.base import Model
from agno.models.message import Message
from agno.models.response import ModelResponse

logger = logging.getLogger(__name__)

CODEX_BASE_URL = "https://chatgpt.com/backend-api"
CODEX_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
_JWT_AUTH_CLAIM = "https://api.openai.com/auth"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _decode_jwt_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


def _extract_account_id(access_token: str) -> str:
    payload = _decode_jwt_payload(access_token)
    return payload.get(_JWT_AUTH_CLAIM, {}).get("chatgpt_account_id", "")


def load_codex_credentials() -> tuple[str, str] | None:
    """Return (access_token, account_id) from ~/.codex/auth.json.

    Auto-refreshes using the stored refresh_token when the access token is
    within 5 minutes of expiry. Returns None if credentials are missing.
    """
    import urllib.parse
    import urllib.request
    from pathlib import Path

    auth_path = Path.home() / ".codex" / "auth.json"
    if not auth_path.exists():
        logger.warning("~/.codex/auth.json not found — run `codex login` first")
        return None

    try:
        auth = json.loads(auth_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read ~/.codex/auth.json: %s", exc)
        return None

    tokens = auth.get("tokens", {})
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")

    if not access_token:
        return None

    # Refresh if expiring soon
    try:
        payload = _decode_jwt_payload(access_token)
        exp = payload.get("exp", 0)
        if exp - time.time() < 300 and refresh_token:
            body = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CODEX_CLIENT_ID,
            }).encode()
            req = urllib.request.Request(
                "https://auth.openai.com/oauth/token",
                data=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                new_tokens = json.loads(resp.read())
            access_token = new_tokens.get("access_token", access_token)
            tokens["access_token"] = access_token
            tokens["refresh_token"] = new_tokens.get("refresh_token", refresh_token)
            auth["tokens"] = tokens
            from datetime import datetime, timezone
            auth["last_refresh"] = datetime.now(timezone.utc).isoformat()
            auth_path.write_text(json.dumps(auth, indent=2), encoding="utf-8")
            logger.debug("Codex token refreshed and saved")
    except Exception as exc:
        logger.debug("Token refresh attempt failed (using existing): %s", exc)

    account_id = _extract_account_id(access_token)
    if not account_id:
        logger.warning("Could not extract chatgpt_account_id from JWT — requests may fail")

    return access_token, account_id


# ---------------------------------------------------------------------------
# Message format conversion: Agno → Codex Responses API
# ---------------------------------------------------------------------------


def _messages_to_codex(messages: List[Message]) -> tuple[str, list]:
    """Convert Agno Message list to (instructions, input_items) for Codex API."""
    instructions = ""
    input_items: list[dict] = []

    for msg in messages:
        role = msg.role
        content = msg.content

        if role == "system":
            instructions = content if isinstance(content, str) else str(content or "")

        elif role == "user":
            if isinstance(content, str):
                parts: list[dict] = [{"type": "input_text", "text": content}]
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        t = part.get("type", "")
                        if t == "text":
                            parts.append({"type": "input_text", "text": part.get("text", "")})
                        elif t == "image_url":
                            url = part.get("image_url", {})
                            if isinstance(url, dict):
                                url = url.get("url", "")
                            parts.append({"type": "input_image", "detail": "auto", "image_url": url})
                    elif isinstance(part, str):
                        parts.append({"type": "input_text", "text": part})
            else:
                parts = [{"type": "input_text", "text": str(content or "")}]

            input_items.append({"role": "user", "content": parts})

        elif role == "assistant":
            tool_calls = msg.tool_calls or []
            if tool_calls:
                for tc in tool_calls:
                    tc_id = tc.get("id", "")
                    item_id = ("fc_" + tc_id)[:64]  # Codex item ID prefix + length limit
                    input_items.append({
                        "type": "function_call",
                        "id": item_id,
                        "call_id": tc_id,
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments", "{}"),
                    })
            if content:
                text = content if isinstance(content, str) else str(content)
                input_items.append({
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text, "annotations": []}],
                    "status": "completed",
                    "id": f"msg_{int(time.time())}",
                })

        elif role == "tool":
            output = content if isinstance(content, str) else json.dumps(content)
            input_items.append({
                "type": "function_call_output",
                "call_id": msg.tool_call_id or "",
                "output": output,
            })

    return instructions, input_items


def _tools_to_codex(tools: Optional[List[Dict[str, Any]]]) -> list:
    if not tools:
        return []
    result = []
    for tool in tools:
        if tool.get("type") == "function":
            fn = tool["function"]
            result.append({
                "type": "function",
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {}),
                "strict": False,
            })
    return result


# ---------------------------------------------------------------------------
# SSE parsing helpers
# ---------------------------------------------------------------------------


def _parse_sse_bytes(raw: bytes) -> list[dict]:
    """Parse a complete SSE response body into a list of event dicts."""
    events: list[dict] = []
    for block in raw.decode("utf-8", errors="replace").split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data:"):
                data = line[5:].strip()
                if data == "[DONE]":
                    return events
                try:
                    events.append(json.loads(data))
                except json.JSONDecodeError:
                    pass
    return events


def _events_to_model_response(events: list[dict]) -> ModelResponse:
    """Assemble a complete ModelResponse from all SSE events."""
    from agno.models.response import Metrics

    model_response = ModelResponse()
    model_response.role = "assistant"

    text_parts: list[str] = []
    # call_id → {"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}
    tool_calls: dict[str, dict] = {}
    # item_id (fc_...) → call_id (call_...) — delta events reference item_id, not call_id
    item_id_to_call_id: dict[str, str] = {}

    for event in events:
        etype = event.get("type", "")

        if etype == "response.output_text.delta":
            text_parts.append(event.get("delta", ""))

        elif etype == "response.output_item.added":
            item = event.get("item", {})
            if item.get("type") == "function_call":
                call_id = item.get("call_id", "")
                item_id = item.get("id", "")
                tool_calls[call_id] = {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": item.get("name", ""),
                        "arguments": "",
                    },
                }
                if item_id:
                    item_id_to_call_id[item_id] = call_id

        elif etype == "response.function_call_arguments.delta":
            # Delta events use item_id (fc_...), not call_id (call_...)
            item_id = event.get("item_id", "")
            call_id = item_id_to_call_id.get(item_id, event.get("call_id", ""))
            if call_id in tool_calls:
                tool_calls[call_id]["function"]["arguments"] += event.get("delta", "")

        elif etype in ("response.completed", "response.done"):
            resp = event.get("response", {})
            usage = resp.get("usage", {})
            if usage:
                metrics = Metrics()
                metrics.input_tokens = usage.get("input_tokens", 0)
                metrics.output_tokens = usage.get("output_tokens", 0)
                metrics.total_tokens = usage.get("total_tokens", 0)
                model_response.response_usage = metrics

        elif etype == "error":
            raise RuntimeError(f"Codex API error: {event.get('message', event)}")

    model_response.content = "".join(text_parts) or None
    if tool_calls:
        model_response.tool_calls = list(tool_calls.values())

    return model_response


# ---------------------------------------------------------------------------
# CodexModel — the custom Agno Model implementation
# ---------------------------------------------------------------------------


@dataclass
class CodexModel(Model):
    """Agno-compatible model that calls chatgpt.com/backend-api/codex/responses.

    Uses ChatGPT Plus/Pro OAuth credentials (from `codex login`).
    No API key or billing required — subscription auth only.

    Usage::

        from vandelay.models.openai_codex import CodexModel

        model = CodexModel(id="codex-mini-latest")
        agent = Agent(model=model, ...)
    """

    id: str = "codex-mini-latest"
    name: str = "CodexModel"
    provider: str = "ChatGPT.com (Codex)"
    base_url: str = CODEX_BASE_URL

    # Lazily populated from ~/.codex/auth.json
    _access_token: str | None = None
    _account_id: str | None = None

    def _ensure_credentials(self) -> tuple[str, str]:
        if self._access_token and self._account_id:
            # Re-check expiry
            payload = _decode_jwt_payload(self._access_token)
            if payload.get("exp", 0) > time.time() + 60:
                return self._access_token, self._account_id

        creds = load_codex_credentials()
        if not creds:
            raise ValueError(
                "No Codex OAuth credentials found. "
                "Run: npm install -g @openai/codex && codex login"
            )
        self._access_token, self._account_id = creds
        return self._access_token, self._account_id

    def _build_headers(self, token: str, account_id: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "chatgpt-account-id": account_id,
            "OpenAI-Beta": "responses=experimental",
            "originator": "pi",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "vandelay/1.0",
        }

    def _build_body(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        instructions, input_items = _messages_to_codex(messages)
        codex_tools = _tools_to_codex(tools)
        body: dict = {
            "model": self.id,
            "store": False,
            "stream": True,
            "instructions": instructions,
            "input": input_items,
            "text": {"verbosity": "medium"},
        }
        if codex_tools:
            body["tools"] = codex_tools
            body["tool_choice"] = "auto"
            body["parallel_tool_calls"] = True
        return body

    def _sync_post(self, headers: dict, body: dict) -> bytes:
        import urllib.request

        url = f"{self.base_url}/codex/responses"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()

    async def _async_post(self, headers: dict, body: dict) -> bytes:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("httpx is required for async Codex requests: uv add httpx") from exc

        url = f"{self.base_url}/codex/responses"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, content=json.dumps(body).encode())
            resp.raise_for_status()
            return resp.content

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def invoke(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format=None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice=None,
        run_response=None,
        compress_tool_results: bool = False,
    ) -> ModelResponse:
        token, account_id = self._ensure_credentials()
        headers = self._build_headers(token, account_id)
        body = self._build_body(messages, tools)
        raw = self._sync_post(headers, body)
        events = _parse_sse_bytes(raw)
        return _events_to_model_response(events)

    async def ainvoke(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format=None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice=None,
        run_response=None,
        compress_tool_results: bool = False,
    ) -> ModelResponse:
        token, account_id = self._ensure_credentials()
        headers = self._build_headers(token, account_id)
        body = self._build_body(messages, tools)
        raw = await self._async_post(headers, body)
        events = _parse_sse_bytes(raw)
        return _events_to_model_response(events)

    def invoke_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format=None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice=None,
        run_response=None,
        compress_tool_results: bool = False,
    ) -> Iterator[ModelResponse]:
        import urllib.request

        token, account_id = self._ensure_credentials()
        headers = self._build_headers(token, account_id)
        body = self._build_body(messages, tools)

        url = f"{self.base_url}/codex/responses"
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        # Active tool calls being streamed: call_id → dict
        active_tools: dict[str, dict] = {}
        # item_id (fc_...) → call_id (call_...) for delta accumulation
        item_id_map: dict[str, str] = {}

        with urllib.request.urlopen(req, timeout=120) as resp:
            buffer = b""
            for chunk in iter(lambda: resp.read(4096), b""):
                buffer += chunk
                while b"\n\n" in buffer:
                    block, buffer = buffer.split(b"\n\n", 1)
                    for line in block.split(b"\n"):
                        if not line.startswith(b"data:"):
                            continue
                        data_str = line[5:].strip().decode("utf-8", errors="replace")
                        if data_str == "[DONE]":
                            return
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta = self._parse_provider_response_delta(event)
                        # Track tool call accumulation
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                cid = tc.get("id", "")
                                item_id = tc.pop("_item_id", "")
                                if "_new_call" in tc:
                                    tc.pop("_new_call")
                                    active_tools[cid] = tc
                                    if item_id:
                                        item_id_map[item_id] = cid
                                else:
                                    # Resolve call_id via item_id if direct lookup misses
                                    if not cid and item_id:
                                        cid = item_id_map.get(item_id, "")
                                    if cid in active_tools:
                                        active_tools[cid]["function"]["arguments"] += (
                                            tc["function"]["arguments"]
                                        )
                        if delta.content is not None:
                            yield delta

        # Yield any completed tool calls
        if active_tools:
            final = ModelResponse()
            final.role = "assistant"
            final.tool_calls = list(active_tools.values())
            yield final

    async def ainvoke_stream(
        self,
        messages: List[Message],
        assistant_message: Message,
        response_format=None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice=None,
        run_response=None,
        compress_tool_results: bool = False,
    ) -> AsyncIterator[ModelResponse]:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError("httpx is required for async Codex streaming: uv add httpx") from exc

        token, account_id = self._ensure_credentials()
        headers = self._build_headers(token, account_id)
        body = self._build_body(messages, tools)

        url = f"{self.base_url}/codex/responses"
        active_tools: dict[str, dict] = {}
        # item_id (fc_...) → call_id (call_...) for delta accumulation
        item_id_map: dict[str, str] = {}

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", url, headers=headers, content=json.dumps(body).encode()
            ) as resp:
                resp.raise_for_status()
                buf = ""
                async for chunk in resp.aiter_text():
                    buf += chunk
                    while "\n\n" in buf:
                        block, buf = buf.split("\n\n", 1)
                        for line in block.split("\n"):
                            if not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                return
                            try:
                                event = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            delta = self._parse_provider_response_delta(event)
                            if delta.tool_calls:
                                for tc in delta.tool_calls:
                                    cid = tc.get("id", "")
                                    item_id = tc.pop("_item_id", "")
                                    if "_new_call" in tc:
                                        tc.pop("_new_call")
                                        active_tools[cid] = tc
                                        if item_id:
                                            item_id_map[item_id] = cid
                                    else:
                                        if not cid and item_id:
                                            cid = item_id_map.get(item_id, "")
                                        if cid in active_tools:
                                            active_tools[cid]["function"]["arguments"] += (
                                                tc["function"]["arguments"]
                                            )
                            if delta.content is not None:
                                yield delta

        if active_tools:
            final = ModelResponse()
            final.role = "assistant"
            final.tool_calls = list(active_tools.values())
            yield final

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        if isinstance(response, bytes):
            return _events_to_model_response(_parse_sse_bytes(response))
        if isinstance(response, list):
            return _events_to_model_response(response)
        return ModelResponse()

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        """Parse a single SSE event dict into a partial ModelResponse."""
        delta = ModelResponse()
        if not isinstance(response, dict):
            return delta

        etype = response.get("type", "")

        if etype == "response.output_text.delta":
            delta.content = response.get("delta", "")

        elif etype == "response.output_item.added":
            item = response.get("item", {})
            if item.get("type") == "function_call":
                call_id = item.get("call_id", "")
                item_id = item.get("id", "")
                delta.tool_calls = [{
                    "id": call_id,
                    "_item_id": item_id,  # needed so streaming loop can build item_id_map
                    "type": "function",
                    "function": {"name": item.get("name", ""), "arguments": ""},
                    "_new_call": True,  # marker so invoke_stream knows it's a new call
                }]

        elif etype == "response.function_call_arguments.delta":
            # Delta events carry item_id (fc_...), not call_id — pass both so the
            # streaming loops can resolve the correct tool call entry.
            delta.tool_calls = [{
                "id": response.get("call_id", ""),
                "_item_id": response.get("item_id", ""),
                "type": "function",
                "function": {"name": "", "arguments": response.get("delta", "")},
            }]

        elif etype == "error":
            raise RuntimeError(f"Codex API error: {response.get('message', response)}")

        return delta
