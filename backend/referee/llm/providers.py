"""Narration providers: the Claude Code CLI (subscription), the Anthropic API (token), and deterministic templates."""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

from ..config import Settings


class ProviderError(Exception):
    pass


class Provider(Protocol):
    name: str
    model: str | None

    def complete(self, system: str, user: str, schema: dict[str, Any]) -> str:
        """Return the JSON text of the memo."""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def discover_claude_cli(path_hint: str | None) -> str | None:
    """CLAUDE_CLI_PATH, then PATH, then the Claude Code VS Code extension's bundled binary."""
    candidates: list[str] = []
    if path_hint:
        candidates.append(path_hint)
    found = shutil.which(path_hint or "claude") or shutil.which("claude")
    if found:
        candidates.append(found)
    home = Path.home()
    candidates += [str(home / ".local" / "bin" / "claude.exe"), str(home / ".local" / "bin" / "claude")]
    candidates += sorted(glob.glob(str(home / ".vscode" / "extensions" / "anthropic.claude-code-*" / "resources" / "native-binary" / "claude*")), reverse=True)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


class ClaudeCliProvider:
    """`claude -p` in headless mode. Tools off, no session persistence, structured output through --json-schema."""

    name = "cli"

    def __init__(self, path: str, model: str | None = None, timeout: float = 180.0, max_budget_usd: float = 2.0):
        self.path = path
        self.model = model or None
        self.timeout = timeout
        self.max_budget_usd = max_budget_usd

    def complete(self, system: str, user: str, schema: dict[str, Any]) -> str:
        cmd = [self.path, "-p", "--output-format", "json", "--system-prompt", system, "--tools", "",
               "--no-session-persistence", "--json-schema", json.dumps(schema), "--max-budget-usd", str(self.max_budget_usd)]
        if self.model:
            cmd += ["--model", self.model]
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_ENTRYPOINT")}
        try:
            proc = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=self.timeout, env=env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderError(f"claude cli failed to run: {exc}") from exc
        stdout = proc.stdout.strip()
        if not stdout:
            raise ProviderError(f"claude cli produced no output (exit {proc.returncode}): {proc.stderr.strip()[-400:]}")
        try:
            data = json.loads(stdout)
        except ValueError as exc:
            raise ProviderError(f"claude cli output is not JSON: {stdout[:200]}") from exc
        if isinstance(data, list):  # stream-style output: the result envelope is the last element
            data = next((d for d in reversed(data) if isinstance(d, dict) and d.get("type") == "result"), data[-1])
        if data.get("is_error"):
            raise ProviderError(f"claude cli error: {data.get('result')}")
        structured = data.get("structured_output")
        if structured is not None:
            return json.dumps(structured)
        result = data.get("result")
        if not isinstance(result, str):
            raise ProviderError("claude cli answer had no result text")
        return _strip_fences(result)


class AnthropicApiProvider:
    """Direct Messages API call with the official SDK. Structured output and server-side refusal fallback are
    passed through extra_body so the code does not depend on the installed SDK's parameter list."""

    name = "api"

    def __init__(self, api_key: str, model: str = "claude-opus-5-5", timeout: float = 120.0):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise ProviderError("pip install anthropic to use the API provider") from exc
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=2)
        self.model = model

    def complete(self, system: str, user: str, schema: dict[str, Any]) -> str:
        anthropic = self._anthropic
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system,
                messages=[{"role": "user", "content": user}],
                extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
                extra_body={"output_config": {"format": {"type": "json_schema", "schema": schema}}, "fallbacks": "default"},
            )
        except anthropic.RateLimitError as exc:
            raise ProviderError(f"rate limited: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"api error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"network error: {exc}") from exc
        if response.stop_reason == "refusal":
            raise ProviderError("the model declined to answer")
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        if not text:
            raise ProviderError("empty answer")
        return _strip_fences(text)


class TemplateProvider:
    """No model. The memo is rendered from the view by referee.llm.prompts.template_memo."""

    name = "template"
    model = None

    def complete(self, system: str, user: str, schema: dict[str, Any]) -> str:  # pragma: no cover - never called
        raise ProviderError("template provider renders directly")


def select_provider(settings: Settings, requested: str | None = None) -> Provider:
    """auto: API when a key is present, else the CLI when a binary is found, else templates."""
    choice = (requested or settings.llm_provider or "auto").lower()
    if choice == "api":
        if not settings.anthropic_api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        return AnthropicApiProvider(settings.anthropic_api_key, settings.anthropic_model)
    if choice == "cli":
        path = discover_claude_cli(settings.claude_cli_path)
        if not path:
            raise ProviderError("claude CLI not found; set CLAUDE_CLI_PATH")
        return ClaudeCliProvider(path, settings.claude_cli_model)
    if choice == "template":
        return TemplateProvider()
    if settings.anthropic_api_key:
        return AnthropicApiProvider(settings.anthropic_api_key, settings.anthropic_model)
    path = discover_claude_cli(settings.claude_cli_path)
    if path:
        return ClaudeCliProvider(path, settings.claude_cli_model)
    return TemplateProvider()
