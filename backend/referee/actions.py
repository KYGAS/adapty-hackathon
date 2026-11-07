"""Dry-run commands. Every action is a string the operator can read, copy, or approve; nothing runs here."""

from __future__ import annotations

import json
import shlex

from .models import ActionPreview, ArmStats, TestInput, Verdict


def _cli(parts: list[str]) -> str:
    return " ".join(shlex.quote(p) if " " in p or '"' in p else p for p in parts)


def stop_with_winner(app_id: str, test_id: str, flow_id: str, flow_name: str, arm_title: str,
                     recommended: bool, title: str | None = None, description: str | None = None) -> ActionPreview:
    return ActionPreview(
        id=f"stop_winner:{flow_id}", kind="stop_winner",
        title=title or f"Stop the test and show {arm_title} ({flow_name}) to everyone",
        description=description or "Ends the test on this placement. The whole audience gets the winning flow. This cannot be undone.",
        recommended=recommended, risk="irreversible",
        cli_command=_cli(["adapty", "ab-tests", "stop", test_id, "--app", app_id, "--winner", flow_id, "--yes"]),
        api_method="POST", api_path=f"/apps/{app_id}/ab-tests/{test_id}/stop/",
        api_body={"winner_flow_id": flow_id},
    )


def keep_running(wait_days: float, decision_date: str | None, recommended: bool = True) -> ActionPreview:
    eta = f" Re-check around {decision_date}." if decision_date else ""
    return ActionPreview(
        id="keep_running", kind="keep_running", title="Keep the test running",
        description=f"No change. The referee re-evaluates on every refresh.{eta}",
        recommended=recommended, risk="none",
        cli_command=None, api_method=None, api_path=None, api_body=None, requires_approval=False,
    )


def start_draft(app_id: str, test: TestInput) -> ActionPreview:
    parts = ["adapty", "ab-tests", "start", test.test_id, "--app", app_id, "--placement", test.placement_id or "<placement-id>"]
    if test.segment_ids:
        parts += ["--segment", test.segment_ids[0]]
    else:
        parts += ["--all-users"]
    parts += ["--yes"]
    audience = "one segment" if test.segment_ids else "All users"
    return ActionPreview(
        id="start_draft", kind="start_draft", title=f"Run the draft on {test.placement_title or 'its placement'}",
        description=f"Starts the A/B test for {audience}. The placement audience switches to the test; reversible by stopping it.",
        recommended=True, risk="reversible",
        cli_command=_cli(parts), api_method="POST", api_path=f"/apps/{app_id}/ab-tests/{test.test_id}/start/",
        api_body={"placement_id": test.placement_id, "segment_ids": list(test.segment_ids)},
    )


def build_actions(app_id: str, test: TestInput, verdict: Verdict, control: ArmStats, leader: ArmStats | None) -> list[ActionPreview]:
    code = verdict.code
    decision_date = verdict.decision_date.strftime("%d %b %Y").lstrip("0") if verdict.decision_date else None
    if code == "NOT_STARTED":
        return [start_draft(app_id, test)]
    if code == "COMPLETED":
        return [ActionPreview(id="none", kind="none", title="Nothing to do", description="The test is finished. Read the audit.",
                              recommended=True, risk="none", cli_command=None, api_method=None, api_path=None,
                              api_body=None, requires_approval=False)]
    if code == "CALL_WINNER" and leader is not None:
        return [stop_with_winner(app_id, test.test_id, leader.flow_id, leader.flow_name, leader.title, True),
                keep_running(0.0, None, recommended=False)]
    if code == "CALL_NO_DIFFERENCE":
        return [stop_with_winner(app_id, test.test_id, control.flow_id, control.flow_name, control.title, True,
                                 title=f"Stop the test and keep the control ({control.flow_name})",
                                 description="No detectable difference at the planned minimum effect. Keeping the control frees the placement for the next test."),
                keep_running(0.0, None, recommended=False)]
    actions = [keep_running(verdict.wait_days, decision_date)]
    if leader is not None:
        actions.append(stop_with_winner(app_id, test.test_id, leader.flow_id, leader.flow_name, leader.title, False,
                                        title=f"Override: stop now with {leader.title} ({leader.flow_name})",
                                        description="Not recommended by the referee. Listed so the override is explicit and logged."))
    return actions


def action_as_text(action: ActionPreview) -> str:
    lines = [f"# {action.title}", f"# {action.description}"]
    if action.cli_command:
        lines.append(action.cli_command)
    if action.api_method:
        lines.append(f"# {action.api_method} {action.api_path} {json.dumps(action.api_body)}")
    return "\n".join(lines)
