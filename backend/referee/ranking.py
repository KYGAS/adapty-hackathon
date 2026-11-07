"""Which placement should get the next test? Idle placements ranked by the money flowing through them."""

from __future__ import annotations

from .actions import start_draft
from .adapty.normalize import build_test_input
from .catalog import Catalog
from .models import PlacementOpportunity


def rank_placements(app_id: str, placements: list[dict], tests: list[dict], flows: list[dict],
                    flow_metrics: list[dict], catalog: Catalog, test_details: dict[str, dict]) -> list[PlacementOpportunity]:
    flow_by_name = {f.get("name"): f for f in flows}
    metrics_by_flow = {m.get("flow_id"): m for m in flow_metrics}
    live_by_placement = {t["placement"]["placement_id"] for t in tests if t.get("state") == "live"}
    drafts_by_placement: dict[str, dict] = {}
    for t in tests:
        if t.get("state") == "draft":
            drafts_by_placement.setdefault(t["placement"]["placement_id"], t)

    rows: list[PlacementOpportunity] = []
    for placement in placements:
        developer_id = placement.get("developer_id", "")
        flow_names = catalog.flows_for_placement(developer_id)
        views = revenue = 0.0
        for name in flow_names:
            flow = flow_by_name.get(name)
            metrics = metrics_by_flow.get(flow["id"]) if flow else None
            if metrics:
                views += float(metrics.get("views", 0) or 0)
                revenue += float(metrics.get("revenue", 0.0) or 0.0)
        rpv = revenue / views if views else 0.0
        has_live = placement["id"] in live_by_placement
        draft = drafts_by_placement.get(placement["id"])
        action = None
        if draft:
            detail = test_details.get(draft["ab_test_id"], {**draft, "flows": [], "goal": None})
            action = start_draft(app_id, build_test_input(detail, None, None, catalog))
        if has_live:
            suggestion = "Busy: a test is live here."
            score = 0.0
        elif draft:
            suggestion = f"Start the draft '{draft['title']}': the placement is idle and the test is ready."
            score = revenue + views * 0.1 + 1000.0
        elif views == 0:
            suggestion = "No attributed traffic yet. Not worth a test until it has viewers."
            score = 0.0
        else:
            suggestion = f"Idle with ${revenue:,.0f} lifetime revenue on {int(views)} views. Draft a test here next."
            score = revenue + views * 0.1
        rows.append(PlacementOpportunity(
            placement_id=placement["id"], developer_id=developer_id, title=placement.get("title", developer_id),
            has_live_test=has_live, draft_test_id=draft["ab_test_id"] if draft else None,
            draft_test_title=draft["title"] if draft else None, flows=flow_names,
            views=int(views), revenue=revenue, revenue_per_viewer=rpv, score=score, rank=0,
            suggestion=suggestion, action=action,
        ))
    rows.sort(key=lambda r: (-r.score, r.title))
    return [row.model_copy(update={"rank": index + 1}) for index, row in enumerate(rows)]
