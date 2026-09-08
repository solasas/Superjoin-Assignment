"""Pluggable LLM backend.

Two implementations of the same tiny interface (`complete`):

  claude_cli    - shells out to the local `claude` CLI in headless mode
                  (`claude -p ... --output-format json`). Zero extra setup
                  if Claude Code is already installed/authenticated on this
                  machine (which is how this project was built and tested),
                  but each call pays CLI startup + full session overhead, so
                  it's noticeably slower and noisier than a direct API call.

  anthropic_api - calls the Anthropic Messages API directly with an API key
                  (ANTHROPIC_API_KEY). Faster, cheaper per call, and is what
                  you'd actually deploy. This is the recommended path for
                  grading without depending on any CLI login state.

Swapping backends is one env var (LLM_BACKEND); nothing else in the
pipeline knows or cares which one is in use.
"""
from __future__ import annotations

import abc
import asyncio
import json
import re

from . import config


def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_loose(text: str):
    """Try hard to get a JSON value out of an LLM response: strip code
    fences, then fall back to slicing out the first {...} or [...] block if
    the model added any stray prose around it.
    """
    text = strip_json_fences(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for open_c, close_c in (("[", "]"), ("{", "}")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from LLM response: {text[:300]!r}")


class LLMError(RuntimeError):
    pass


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def complete(self, prompt: str, *, model: str, system: str | None = None) -> str:
        ...


class ClaudeCLIClient(LLMClient):
    def __init__(self, timeout_seconds: int | None = None):
        self.timeout_seconds = timeout_seconds or config.LLM_TIMEOUT_SECONDS

    async def complete(self, prompt: str, *, model: str, system: str | None = None) -> str:
        argv = [
            "claude", "-p", prompt,
            "--model", model,
            "--output-format", "json",
            "--restricted",
            "--strict-mcp-config",
        ]
        if system:
            argv += ["--system-prompt", system]

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise LLMError(f"claude CLI timed out after {self.timeout_seconds}s")

        if proc.returncode != 0:
            raise LLMError(f"claude CLI exited {proc.returncode}: {stderr.decode(errors='replace')[:500]}")

        raw = stdout.decode(errors="replace").strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMError(f"claude CLI produced non-JSON envelope: {raw[:500]!r}") from e

        if payload.get("is_error"):
            raise LLMError(f"claude CLI reported an error: {payload.get('result')}")

        result = payload.get("result")
        if not isinstance(result, str):
            raise LLMError(f"claude CLI envelope missing 'result': {payload}")
        return result


class AnthropicAPIClient(LLMClient):
    def __init__(self, api_key: str | None = None):
        api_key = api_key or config.ANTHROPIC_API_KEY
        if not api_key:
            raise LLMError("LLM_BACKEND=anthropic_api but ANTHROPIC_API_KEY is not set")
        import anthropic  # imported lazily so claude_cli mode never needs this package configured

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(self, prompt: str, *, model: str, system: str | None = None) -> str:
        kwargs = dict(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.create(**kwargs)
        except Exception as e:  # pragma: no cover - network/SDK errors
            raise LLMError(str(e)) from e
        return "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")


_client_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client_singleton
    if _client_singleton is not None:
        return _client_singleton
    if config.LLM_BACKEND == "anthropic_api":
        _client_singleton = AnthropicAPIClient()
    else:
        _client_singleton = ClaudeCLIClient()
    return _client_singleton
