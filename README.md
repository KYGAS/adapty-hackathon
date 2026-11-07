# Adapty Experimentation Referee

An automated decision copilot that stops premature A/B test calls. Deterministic sample-size and trial-lag statistics decide, a constrained LLM narrates, and every change to a live test is a dry-run Adapty CLI command until a human approves it.

Built for Adapty Hackathon Belgrade, 7-8 Nov 2026, on the seeded Lumen app.

## What it does

| Problem | What the referee adds on top of Adapty's P2BB |
|---|---|
| Peeking: stopping on a good day | Required viewers per arm for the planned effect, progress, and the date the sample is reached |
| Trial-lag blindness: day-one cash vs open 7-day trials | Open trials times the historical trial-to-paid rate times the plan price, per arm, and whether that can flip the leader |
| No retroactive check | Audit grade for completed tests plus realized revenue per viewer of the winner vs the alternative |
| Idle placements | Placements ranked by the money flowing through them; a ready draft jumps the queue |
| Risky one-click writes | Every action is a dry-run `adapty ab-tests ...` command; execution needs an approval, is logged, and live writes stay off by default |

On the seeded data: Onboarding (P2BB 100% for B) gets "Wait: 137 open trials can still flip the leader, earliest safe call 15 Nov 2026"; the North America main paywall test gets "Not decidable at this traffic: 16,792 viewers per arm needed"; the draft is ranked the next test to start; the completed Settings test audits as grade F and is reversed by realized revenue.

## Layout

| Path | What |
|---|---|
| `backend/referee/stats/` | Pure statistics, standard library only, 100% branch coverage enforced |
| `backend/referee/adapty/` | Adapty developer API client (live) and a fixture-backed mock answering the same routes, with mocked writes |
| `backend/referee/dossier.py` | Inputs to a typed `TestDossier` |
| `backend/referee/llm/` | Narration view, Claude Code CLI / Anthropic API / template providers, number guard |
| `backend/referee/api/` | FastAPI routes and the read-only CORS proxy to the Adapty API |
| `frontend/` | React dashboard mirroring app.adapty.io (A/B tests, metrics, placements) plus the Experiment Referee pages |
| `docs/` | `architecture.md`, `adapty-developer-api.md` |

## Run it

Backend (Python 3.12+, tested on 3.14):

```bash
cd backend
pip install -r requirements.txt
python -X utf8 -m referee          # http://localhost:8010  (OpenAPI docs at /docs), mock data by default
python -X utf8 -m pytest           # 129 tests, statistics at 100% coverage
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173, proxies /api and /adapty to the backend
```

Or both at once: `scripts/dev.ps1` (Windows) or `bash scripts/dev.sh`.

## Configuration

Copy `.env.example` to `.env`. Everything has a demo default.

| Variable | Meaning |
|---|---|
| `ADAPTY_MODE` | `mock` serves fixtures; `live` calls api-admin.adapty.io |
| `ADAPTY_FIXTURES` | `expanded` (default): ten tests over four months built from the offline Lumen dataset, clock frozen at 7 Nov 2026 17:00 UTC; `captured`: the real one-day answers. See `docs/demo-dataset-plan.md` |
| `ADAPTY_TOKEN` | developer token; empty reads `%LOCALAPPDATA%\adapty\config.json` from `adapty auth login` |
| `REFEREE_ALLOW_LIVE_WRITES` | `false` by default: approved actions are logged but never reach a live app |
| `LLM_PROVIDER` | `auto`, `cli` (Claude Code subscription), `api` (`ANTHROPIC_API_KEY`), `template` |
| `REFEREE_NOW` | freeze the clock (ISO 8601) for reproducible demos |

## Demo path

1. `/ab-tests/flows`: the Adapty list with a Referee verdict in each card's meta row.
2. Open "Onboarding: annual trial vs weekly first" metrics: P2BB says B at 100%, the referee says wait, with the timeline and the projected revenue per viewer once the 66 annual trials resolve.
3. Write memo: the LLM narrates the dossier; the badge shows the number guard passed.
4. `/referee`: verdicts for every test, the ranked next placement, the decision log.
5. Approve "Run the draft" on the AI limit test: dry run first, then approval with a name; in mock mode the draft goes live and the dashboard updates.

## API

| Route | Purpose |
|---|---|
| `GET /api/referee/tests` | verdict per test (query `mde`, `alpha`, `power`, `max_wait`, `min_runtime` override the plan) |
| `GET /api/referee/tests/{id}/dossier` | the full TestDossier |
| `POST /api/referee/tests/{id}/memo` | narration `{provider?: auto|cli|api|template}` |
| `GET /api/referee/opportunities` | idle placements ranked |
| `POST /api/referee/actions/execute` | `{test_id, action_id, approved, approver, note?}`; dry run unless approved |
| `GET /api/referee/audit-log` | every dry run, approval, block and failure |
| `ANY /adapty/{path}` | proxy to the Adapty developer API; reads only, writes answer 403 |

## Invariants

1. The LLM never calculates. It narrates a dossier the statistics produced; a guard rejects any number that is not in the dossier view and falls back to a deterministic template.
2. Every statistic is a pure Python function with unit tests (`backend/referee/stats`).
3. No autonomous writes. Mutations run only through `/api/referee/actions/execute` after an explicit approval, and only against a live app when `REFEREE_ALLOW_LIVE_WRITES=true`.
