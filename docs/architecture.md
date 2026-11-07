# Architecture

## One sentence

Adapty data comes in through one client interface (live API or captured fixtures), pure Python statistics turn it into a typed TestDossier, an LLM narrates the dossier under a number guard, and every mutation is a dry-run command until a human approves it in the UI.

## Data flow

```
Adapty developer API ----\                                     React dashboard (Vite)
  api-admin.adapty.io     \   referee/adapty/client.py          |  /adapty/*  (read-only proxy, same routes)
                            > AdaptyClient (live | mock) ----->  |  /api/referee/* (dossier, memo, actions)
captured fixtures --------/            |                          v
  referee/adapty/fixtures/             v                    DossierPanel, TestCard, RefereePage
                              normalize.py -> TestInput
                                       |
                                       v
                              dossier.py  (pure)  <- stats/*  (pure, 100% covered)
                                       |
                        +--------------+----------------+
                        v              v                v
                 TestDossier     actions.py        audit.py / ranking.py
                        |        (dry-run CLI)
                        v
                 llm/narrate.py  -> providers (Claude CLI | Anthropic API | template)
                        |             + guard.py (every digit must exist in the dossier view)
                        v
                 Memo (headline, summary, markdown, risks, next steps)
```

## Invariants and where they are enforced

| Invariant | Enforcement |
|---|---|
| Zero LLM math | `llm/prompts.py` sends a pre-rounded view; `llm/guard.py` extracts every number from the memo and rejects tokens absent from the view; one corrective retry, then the deterministic template memo is served with `guard_passed=false`. Tested in `tests/test_guard.py`. |
| Deterministic, unit-tested statistics | `referee/stats/` is standard library only, reads no clock or network; pytest enforces 100% branch coverage (`pyproject.toml`). |
| No autonomous writes | `api/proxy.py` refuses every non-read method. `service.execute()` recomputes the dossier, requires `approved=true` and an approver name, refuses live writes unless `REFEREE_ALLOW_LIVE_WRITES=true`, and appends every dry run, approval, block and failure to `backend/data/audit_log.jsonl`. |

## Decision rules (stats/decision.py)

Rules fire in a fixed order; the first blocking one wins:

1. draft -> NOT_STARTED; completed or archived -> COMPLETED (audit instead)
2. open trials could flip the leader -> WAIT_TRIAL_LAG (wait until the last trial matures plus a grace day)
3. no viewers yet -> WAIT_SAMPLE (first read after a full week)
4. planned sample unreachable within the wait limit -> NOT_DECIDABLE (suggest a bolder change or wider audience; report the effect detectable by the horizon)
5. leader under 50 payers -> INSUFFICIENT_PAYERS (Adapty's revenue range is zero to twice the mean below that)
6. sample reached: under 7 days -> WAIT_MIN_RUNTIME; significant after Holm correction and P2BB >= 95 -> CALL_WINNER; otherwise CALL_NO_DIFFERENCE
7. otherwise WAIT_SAMPLE with the date the smallest arm reaches the plan

Sample size uses the pooled two-sided z-test formula (alpha 0.05, power 0.8, 20% relative MDE by default; the UI can change the MDE). Pending revenue per arm is open trials times the account's historical trial-to-paid rate (Wilson interval) times the trial plan price; the low bound pairs the low rate with the cheapest plan and the high bound the high rate with the dearest.

## Adapty API fidelity

The backend speaks the developer API's own routes and bodies (`docs/adapty-developer-api.md`). The mock store answers the same paths from captured fixtures and mutates them on start, stop, create and archive, so the frontend code is identical in mock and live mode. Adding the referee to Adapty would mean: reading `ab-tests/{id}/metrics/total/` and `analytics/conversion/` (trial-paid), running `referee/stats`, and surfacing the verdict next to P2BB on the metrics page.

## Running modes

| Variable | Effect |
|---|---|
| `ADAPTY_MODE=mock` | fixtures, writes mutate memory only |
| `ADAPTY_MODE=live` | real API with the CLI token; reads only unless `REFEREE_ALLOW_LIVE_WRITES=true` |
| `LLM_PROVIDER=auto` | API key if set, else Claude Code CLI if found, else template |
| `REFEREE_NOW` | freezes the clock for reproducible demos |
