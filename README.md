# Adapty Experimentation Referee

Stop calling A/B tests before the money is in. The referee sits next to Adapty's P2BB and answers the question P2BB does not: are we allowed to call this test yet? Deterministic statistics decide, an LLM explains without doing any math, and every change to a live test waits for a named human approval.

Built during Adapty Hackathon Belgrade, 7-8 Nov 2026, on the seeded Lumen app. How we used AI: [AI_LOG.md](AI_LOG.md).

## What it does

P2BB says who is ahead. Two things still make teams call too early. Peeking: checking daily and stopping on a lucky day. Trial lag: a weekly plan pays today, an annual trial pays after 7 days, so the cheap plan always looks like the winner on day one. The referee gives every A/B test one verdict and, when the verdict is to wait, a date.

| Feature | What you get |
|---|---|
| Sample size gate | Viewers each arm needs for the planned effect, progress, and the day the sample is reached |
| Trial lag | Open trials priced at the account's own trial-to-paid rate, per arm, and whether they can still flip the leader |
| Verdict | Call it (winner, or no difference), wait for trials, wait for sample, minimum runtime, too few payers, or not decidable at this traffic |
| Audit | A grade for every completed test, checked against the revenue that followed |
| Next test | Idle placements ranked by the revenue flowing through them, a ready draft first |
| Safe actions | Each action is a dry-run `adapty ab-tests` command; running it needs a named approval and is logged |
| Memo | Claude writes a short explanation from the statistics; a guard rejects any number that is not in them |

On the demo data, "Onboarding: annual trial vs weekly first" shows P2BB 100% for B. The referee says "Wait: 85 open trials can still flip the leader. Earliest safe call 15 Nov 2026." The North America main paywall test is not decidable at its traffic: 2,402 viewers per arm are needed, 145 days away. The three-arm main paywall test is a winner after Holm correction. Completed tests grade A, C and F, and the realized revenue reversed the winner of the C-grade test.

## Who it's for

- Growth and product managers who run paywall and onboarding tests in Adapty and have to decide when to stop them.
- Analysts who want sample size and trial lag handled the same way every time, with the assumptions on screen.
- Adapty itself: the referee reads only data the dashboard already serves, so it could ship as a panel next to P2BB.

## How to run it

No accounts, keys or environment variables are needed. The default mode serves built-in demo data and cannot write to Adapty.

Requirements: Python 3.12 or newer, Node.js 20.19 or newer.

```bash
# Backend, terminal 1: http://localhost:8010 (API docs at /docs)
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -X utf8 -m referee

# Frontend, terminal 2: http://localhost:5173
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Unit tests: `python -X utf8 -m pytest` in `backend` (134 tests, statistics at 100% branch coverage).

- **Ports taken:** set `REFEREE_PORT=8020` for the backend and run the frontend with `VITE_BACKEND_URL=http://localhost:8020 npm run dev -- --port 5174`.
- **Memo:** with Claude Code installed and logged in, "Write memo" uses it automatically. Without it you get a deterministic template memo that passes the same guard.
- **Reset the demo:** restart the backend, or `POST http://localhost:8010/api/dev/reset`.

Try this:

1. A/B tests page: each live test card carries a Referee verdict next to its audience and placement.
2. Open "Onboarding: annual trial vs weekly first" with View metrics and scroll to Experiment Referee: the wait verdict, the timeline, and the money still in open trials.
3. Click Write memo, change "Planned minimum effect", and use "Group by" to split the table by country or store.
4. Experiment Referee in the sidebar: all ten verdicts, the audits, and where to test next.
5. On "AI edits limit reached" click Approve and run, type a name, confirm. The draft goes live in demo memory and the decision log records who approved which command.

Optional configuration (copy `.env.example` to `.env`):

| Variable | Meaning |
|---|---|
| `ADAPTY_MODE` | `mock` (default) serves fixtures; `live` calls api-admin.adapty.io |
| `ADAPTY_FIXTURES` | `expanded` (default) is the four-month demo set; `captured` is the real one-day answers from the Lumen app |
| `ADAPTY_TOKEN` | Adapty developer token for live mode; empty reads the token saved by `adapty auth login` |
| `REFEREE_ALLOW_LIVE_WRITES` | `false` by default: approved actions are logged but never reach a live app |
| `LLM_PROVIDER` | `auto`, `cli` (Claude Code), `api` (`ANTHROPIC_API_KEY`), `template` |
| `REFEREE_NOW` | freeze the clock (ISO 8601) for reproducible demos |

## What's real vs mocked

| Part | Status |
|---|---|
| Adapty API routes, request bodies, field names | Real. Mapped from the Adapty CLI 0.18 source and confirmed with read-only calls on the seeded Lumen app |
| `captured` fixtures | Real answers from the Lumen app: four A/B tests, one day of traffic |
| `expanded` demo data (default) | Generated by `backend/scripts/expand_seed.py` from the organizers' offline Lumen dataset: 50,000 synthetic users over 120 days. Six of the ten tests and five flows exist only in this set. The clock is frozen at 7 Nov 2026 17:00 UTC |
| Statistics, verdicts, audits, ranking | Real. Computed on every request, nothing precomputed |
| Memo through the Claude Code CLI | Real and tested |
| Memo through the Anthropic API | Implemented, not tested with a real key |
| Writes: start, stop | Mocked in mock mode: they change the in-memory store and the decision log. Live writes need `REFEREE_ALLOW_LIVE_WRITES=true` and were never enabled |
| Live mode | Implemented on the same client interface, not tested end to end |
| Trial-to-paid rates | Taken from the account's history per product, not measured inside the test. Each dossier says so |
| Dashboard around the referee | A look-alike of app.adapty.io. A/B tests, metrics and placements pages run on the data. Other sidebar pages are placeholders, and Duplicate, Modify, CSV export and placement edits only show a notice |

Only flow A/B tests are covered. Paywall and crossplacement tests are not.

## Architecture

```
Adapty developer API (live) or fixtures (mock)
  -> referee/adapty    one client interface, the same routes and shapes in both modes
  -> referee/stats     pure Python, standard library only, 100% branch coverage enforced
  -> referee/dossier   one typed TestDossier per test; fixed-order rules pick the verdict
  -> referee/llm       Claude narrates a pre-rounded view; a guard rejects unknown numbers
  -> referee/api       FastAPI routes, approval-gated actions, read-only proxy to Adapty
  -> frontend          React 19 and TypeScript on the captured Adapty style kit
```

Three invariants hold in code:

1. **Zero LLM math.** The model only narrates. If the number guard fails twice, the template memo is served.
2. **Tested statistics.** pytest fails below 100% branch coverage on `referee/stats`.
3. **No autonomous writes.** The proxy refuses writes. Execution needs `approved=true` and an approver name, and every attempt is logged.

| Route | Purpose |
|---|---|
| `GET /api/referee/tests` | verdict per test; `mde`, `alpha`, `power`, `max_wait`, `min_runtime` override the plan |
| `GET /api/referee/tests/{id}/dossier` | the full TestDossier |
| `POST /api/referee/tests/{id}/memo` | narration, `{provider?: auto, cli, api, template}` |
| `GET /api/referee/opportunities` | idle placements ranked |
| `POST /api/referee/actions/execute` | `{test_id, action_id, approved, approver}`; a dry run unless approved |
| `GET /api/referee/audit-log` | every dry run, approval, block and failure |
| `ANY /adapty/{path}` | proxy to the Adapty developer API; reads only, writes answer 403 |

More detail: [docs/architecture.md](docs/architecture.md) covers the decision rules. [docs/adapty-developer-api.md](docs/adapty-developer-api.md) lists the routes. [docs/demo-dataset-plan.md](docs/demo-dataset-plan.md) explains the demo data.

## What we'd do next

1. Run live mode read-only against Lumen and diff it with the captured fixtures, then pilot on one real customer app.
2. Measure trial-to-paid inside each test instead of borrowing account history. It would help if Adapty returned it per product in the metrics total response.
3. Test significance on revenue per viewer, not only on paid conversion. Today the dossier warns when the two disagree.
4. Add sequential testing, so checking every day is safe by design and not only guarded against.
5. Cover paywall and crossplacement tests, and notify the team when a test becomes safe to call.

## Sources

- The Adapty style kit in `frontend/public/kit` was captured from app.adapty.io on 7 Nov 2026 during the event. Its fonts are Inter, Inter Tight and Fira Code under the SIL OFL.
- The demo data comes from the organizers' Lumen seed repository. Its offline dataset is copied to `backend/scripts/data`.
