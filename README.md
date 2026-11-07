# Adapty Experimentation Referee

An automated decision copilot that stops premature A/B test calls. It pairs deterministic sample-size and trial-lag statistics with constrained LLM narration, and turns every recommendation into a dry-run Adapty CLI command that a human approves before anything touches a live test.

Built for Adapty Hackathon Belgrade, 7-8 Nov 2026, on the seeded Lumen app.

## Layout

| Path | What |
|---|---|
| `backend/` | Python microservice: Adapty client (mock or live), deterministic statistics, typed TestDossier, LLM narration, approval-gated actions, CORS proxy to the Adapty developer API |
| `frontend/` | React dashboard that mirrors app.adapty.io (A/B tests, metrics, placements) and adds the Referee |
| `docs/` | API notes and architecture |

## Run it

Backend (Python 3.12+):

```bash
cd backend
pip install -r requirements.txt
python -m referee            # http://localhost:8000, mock data by default
python -m pytest             # statistics are unit tested with 100% coverage
```

Frontend (Node 18+):

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173, proxies /api and /adapty to the backend
```

Copy `.env.example` to `.env` to switch to live Adapty data or to pick an LLM provider.

## Invariants

1. The LLM never calculates. It narrates a TestDossier the statistics module produced, and a guard rejects any number that is not in the dossier.
2. Every statistic is a pure Python function with unit tests.
3. No autonomous writes. Mutating Adapty calls run only after an explicit approval in the UI, and only when `REFEREE_ALLOW_LIVE_WRITES=true`.
