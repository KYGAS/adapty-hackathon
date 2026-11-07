"""narrate(): view -> provider -> memo -> guard, with one corrective retry and a deterministic fallback."""

from __future__ import annotations

import json
import time
from typing import Any

from pydantic import ValidationError

from ..config import Settings
from ..models import AuditResult, Memo, Narration, TestDossier
from .guard import check_memo
from .prompts import MEMO_SCHEMA, SYSTEM_PROMPT, narration_view, template_memo, user_prompt
from .providers import ProviderError, TemplateProvider, select_provider


def _parse_memo(text: str) -> Memo:
    try:
        data: Any = json.loads(text)
    except ValueError as exc:
        raise ProviderError(f"memo is not JSON: {text[:160]}") from exc
    try:
        return Memo.model_validate(data)
    except ValidationError as exc:
        raise ProviderError(f"memo does not match the schema: {exc.errors()[:2]}") from exc


def narrate(dossier: TestDossier, settings: Settings, provider_name: str | None = None,
            audit: AuditResult | None = None) -> Narration:
    started = time.monotonic()
    view = narration_view(dossier, audit)
    fallback = template_memo(view)
    try:
        provider = select_provider(settings, provider_name)
    except ProviderError as exc:
        return Narration(provider="template", model=None, memo=fallback, guard_passed=True,
                         guard_violations=[f"provider unavailable: {exc}"], attempts=0, fallback_used=True,
                         elapsed_ms=int((time.monotonic() - started) * 1000))
    if isinstance(provider, TemplateProvider):
        return Narration(provider="template", model=None, memo=fallback, guard_passed=True, attempts=0,
                         fallback_used=False, elapsed_ms=int((time.monotonic() - started) * 1000))

    prompt = user_prompt(view)
    violations: list[str] = []
    attempts = 0
    for attempt in range(2):
        attempts = attempt + 1
        try:
            text = provider.complete(SYSTEM_PROMPT, prompt, MEMO_SCHEMA)
            memo = _parse_memo(text)
        except ProviderError as exc:
            violations = [str(exc)]
            break
        violations = check_memo(memo, view)
        if not violations:
            return Narration(provider=provider.name, model=provider.model, memo=memo, guard_passed=True,
                             attempts=attempts, fallback_used=False, elapsed_ms=int((time.monotonic() - started) * 1000))
        prompt = (user_prompt(view) + "\n\nYour previous memo was rejected by the number guard. These numbers are not in the "
                  "dossier view and must be removed or replaced with values copied from it: " + "; ".join(violations[:8]))
    return Narration(provider=provider.name, model=provider.model, memo=fallback, guard_passed=False,
                     guard_violations=violations, attempts=attempts, fallback_used=True,
                     elapsed_ms=int((time.monotonic() - started) * 1000))
