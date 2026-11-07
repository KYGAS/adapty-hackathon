"""Turn Adapty API answers into the referee's typed inputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..catalog import Catalog
from ..models import ArmInput, HistoryInput, TestInput


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def products_by_arm(tree: dict | None) -> dict[str, list[tuple[str, str]]]:
    """(product_id, title) pairs under each variation of a metrics tree, searching all screens."""
    found: dict[str, list[tuple[str, str]]] = {}
    if not tree:
        return found

    def walk(node: dict, variation: str | None) -> None:
        level = node.get("level")
        if level == "variation":
            variation = node.get("flow_id") or node.get("variation_id")
        if level == "product" and variation:
            pair = (str(node.get("product_id") or node.get("store_product_id") or ""), str(node.get("title") or ""))
            if pair not in found.setdefault(variation, []):
                found[variation].append(pair)
        for child in node.get("items", []) or []:
            walk(child, variation)

    walk(tree, None)
    return found


def build_test_input(detail: dict, total: dict | None, tree: dict | None, catalog: Catalog,
                     winner_flow_id: str | None = None) -> TestInput:
    arm_rows = {m.get("flow_id"): m for m in (total or {}).get("metrics", [])}
    tree_products = products_by_arm(tree)
    arms: list[ArmInput] = []
    for flow in detail.get("flows", []):
        row = arm_rows.get(flow["flow_id"], {})
        pairs = tree_products.get(flow["flow_id"], [])
        products = catalog.resolve([p for p, _ in pairs], [t for _, t in pairs]) if pairs else []
        if not products:
            products = catalog.products_for_flow(flow.get("flow_name", ""))
        arms.append(ArmInput(
            flow_id=flow["flow_id"],
            variation_id=flow.get("variation_id") or row.get("variation_id"),
            title=flow.get("title") or row.get("title") or "?",
            flow_name=flow.get("flow_name") or "?",
            weight=_num(flow.get("weight", row.get("weight")), 50.0),
            views=int(_num(row.get("views"))),
            purchases=int(_num(row.get("purchases"))),
            trials=int(_num(row.get("trials"))),
            payers=int(_num(row.get("unique_paid_subscribers"))),
            revenue=_num(row.get("revenue")),
            p2bb=None if row.get("probability") is None else _num(row.get("probability")),
            range_low=None if row.get("low_boundary") is None else _num(row.get("low_boundary")),
            range_mean=None if row.get("average_per_1000") is None else _num(row.get("average_per_1000")),
            range_high=None if row.get("upper_boundary") is None else _num(row.get("upper_boundary")),
            p_value=None if row.get("p_value") is None else _num(row.get("p_value")),
            active_trials_rate=None if row.get("active_trials_rate") is None else _num(row.get("active_trials_rate")),
            products=products,
        ))
    placement = detail.get("placement") or {}
    return TestInput(
        test_id=detail["ab_test_id"],
        title=detail.get("title", ""),
        goal=detail.get("goal"),
        type=detail.get("type", "flow"),
        state=detail.get("state", "draft"),
        placement_id=placement.get("placement_id"),
        placement_title=placement.get("title"),
        segment_ids=list(detail.get("segment_ids") or []),
        started_at=parse_dt(detail.get("started_at")),
        stopped_at=parse_dt(detail.get("stopped_at")),
        arms=arms,
        winner_flow_id=winner_flow_id,
    )


def build_history_input(conversion: dict | None) -> HistoryInput:
    """Trial-to-paid history from the analytics conversion answer (total segment, finished trials only)."""
    if not conversion:
        return HistoryInput()
    # value_from already excludes trials that are still running (they are reported as value_from_unfinished).
    started = int(_num(conversion.get("value_from")))
    paid = int(_num(conversion.get("value_to")))
    for segment in conversion.get("segments", []) or []:
        if segment.get("is_total"):
            started = int(_num(segment.get("value_from")))
            paid = int(_num(segment.get("value_to")))
            break
    return HistoryInput(trials_started=started, trials_paid=paid)
