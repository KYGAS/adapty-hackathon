"""Zero LLM math, enforced: every digit in a memo must come from the dossier view."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

from ..models import Memo

NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w])")
DATE_RE = re.compile(r"^(\d{1,2}) (\w{3}) (\d{4})$")


def _variants(value: float | int) -> set[str]:
    out: set[str] = set()
    if isinstance(value, bool):
        return out
    if isinstance(value, int):
        out.add(str(value))
        out.add(f"{value:,}")
        out.add(f"{abs(value)}")
        return out
    for digits in (0, 1, 2):
        out.add(f"{value:.{digits}f}")
        out.add(f"{value:,.{digits}f}")
        out.add(f"{abs(value):.{digits}f}")
    if 0.0 <= value <= 1.0:
        for digits in (0, 1, 2):
            out.add(f"{value * 100.0:.{digits}f}")
    return out


def _walk(node: Any) -> Iterable[Any]:
    if isinstance(node, dict):
        for child in node.values():
            yield from _walk(child)
    elif isinstance(node, (list, tuple)):
        for child in node:
            yield from _walk(child)
    else:
        yield node


def allowed_numbers(view: dict[str, Any]) -> set[str]:
    """Normalized number strings (no thousands separators) the memo may contain."""
    allowed: set[str] = set()
    for leaf in _walk(view):
        if isinstance(leaf, bool) or leaf is None:
            continue
        if isinstance(leaf, (int, float)):
            allowed |= {v.replace(",", "") for v in _variants(leaf)}
        elif isinstance(leaf, datetime):
            allowed |= {str(leaf.day), str(leaf.year)}
        elif isinstance(leaf, str):
            match = DATE_RE.match(leaf)
            if match:
                allowed |= {match.group(1), match.group(3)}
            else:
                # Numbers embedded in strings the view already contains (headline, product labels, commands) are fair game.
                for m in NUMBER_RE.finditer(leaf):
                    allowed.add(_normalize(m))
    return allowed


def _normalize(match: re.Match[str]) -> str:
    whole = match.group(1).replace(",", "")
    frac = match.group(2)
    return f"{whole}.{frac}" if frac else whole


def extract_numbers(text: str) -> list[str]:
    return [_normalize(m) for m in NUMBER_RE.finditer(text)]


def _equivalent(token: str, allowed: set[str]) -> bool:
    if token in allowed:
        return True
    try:
        value = float(token)
    except ValueError:
        return False
    for candidate in allowed:
        try:
            if abs(float(candidate) - value) < 1e-9:
                return True
        except ValueError:
            continue
    return False


def check_text(text: str, allowed: set[str]) -> list[str]:
    violations: list[str] = []
    for match in NUMBER_RE.finditer(text):
        token = _normalize(match)
        if not _equivalent(token, allowed):
            start = max(0, match.start() - 25)
            snippet = text[start:match.end() + 25].replace("\n", " ")
            violations.append(f"{token} in '...{snippet}...'")
    return violations


def check_memo(memo: Memo, view: dict[str, Any]) -> list[str]:
    allowed = allowed_numbers(view)
    text = "\n".join([memo.headline, memo.summary, memo.memo_markdown, *memo.risks, *memo.next_steps])
    return check_text(text, allowed)
