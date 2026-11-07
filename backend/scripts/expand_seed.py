#!/usr/bin/env python
"""Generate the expanded demo fixture set from the hackathon's offline Lumen dataset.

The captured fixtures (backend/referee/adapty/fixtures) are real Adapty answers for one day of traffic.
This script rebuilds the same API answers from the 50,000-user offline dataset that seeded Lumen
(adapty-seed-data-hack/data/offline), so the mock store can serve months of attributed traffic,
per-day series and more tests. Nothing here talks to Adapty.

Usage (from backend/):
    python -X utf8 scripts/expand_seed.py analyze                 # print what the offline data holds
    python -X utf8 scripts/expand_seed.py build [--now ISO] [--seed N]   # write fixtures_expanded/

Deterministic: same inputs, same clock, same seed -> identical files.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
CAPTURED = BACKEND / "referee" / "adapty" / "fixtures"
EXPANDED = BACKEND / "referee" / "adapty" / "fixtures_expanded"
DEFAULT_OFFLINE = [BACKEND / "scripts" / "data", REPO.parent / "adapty-seed-data-hack" / "data" / "offline"]
DEFAULT_NOW = "2026-11-07T17:00:00Z"
DEFAULT_SEED = 20261107

sys.path.insert(0, str(BACKEND))


# ----------------------------------------------------------------------------- offline dataset


@dataclass
class Tx:
    user_id: str
    seq: int
    purchase_type: str
    product: str
    store_product_id: str
    purchased_at: datetime
    expires_at: datetime | None
    price_usd: float
    is_trial: bool
    refunded_at: datetime | None


@dataclass
class User:
    user_id: str
    platform: str
    country: str
    install_at: datetime
    placement: str
    flow: str
    ab_test: str | None
    tx: list[Tx] = field(default_factory=list)


def _dt(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def find_offline_dir(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else DEFAULT_OFFLINE
    for path in candidates:
        if (path / "users.csv.gz").exists() and (path / "transactions.csv.gz").exists():
            return path
    raise SystemExit("offline dataset not found; pass --offline DIR holding users.csv.gz and transactions.csv.gz")


def load_offline(path: Path) -> dict[str, User]:
    users: dict[str, User] = {}
    with gzip.open(path / "users.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            users[row["user_id"]] = User(
                user_id=row["user_id"], platform=row["platform"], country=row["country"],
                install_at=_dt(row["install_at"]) or datetime.now(timezone.utc),
                placement=row["placement"], flow=row["flow"], ab_test=row["ab_test"] or None,
            )
    with gzip.open(path / "transactions.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            user = users.get(row["user_id"])
            if user is None:
                continue
            user.tx.append(Tx(
                user_id=row["user_id"], seq=int(row["seq"]), purchase_type=row["purchase_type"],
                product=row["product"], store_product_id=row["store_product_id"],
                purchased_at=_dt(row["purchased_at"]) or user.install_at, expires_at=_dt(row["expires_at"]),
                price_usd=float(row["price_usd"] or 0.0), is_trial=row["offer"] == "free_trial",
                refunded_at=_dt(row["refunded_at"]),
            ))
    for user in users.values():
        user.tx.sort(key=lambda t: (t.purchased_at, t.seq))
    return users


# ----------------------------------------------------------------------------- analysis


def analyze(users: dict[str, User]) -> None:
    installs = sorted(u.install_at for u in users.values())
    print(f"users {len(users):,}  installs {installs[0].date()} .. {installs[-1].date()}")
    by_test: dict[str, Counter] = defaultdict(Counter)
    payers: dict[str, Counter] = defaultdict(Counter)
    revenue: dict[str, Counter] = defaultdict(Counter)
    for u in users.values():
        key = u.ab_test or "(no test)"
        by_test[key][u.flow] += 1
        paid = [t for t in u.tx if not t.is_trial and t.refunded_at is None]
        if paid:
            payers[key][u.flow] += 1
            revenue[key][u.flow] += sum(t.price_usd for t in paid)
    for test, flows in by_test.items():
        print(f"\n{test}")
        for flow, n in flows.most_common():
            print(f"  {flow:14} users {n:6,}  payers {payers[test][flow]:5,}  revenue ${revenue[test][flow]:10,.0f}  "
                  f"rpv ${revenue[test][flow] / n:6.2f}")
    trials = Counter()
    converted = Counter()
    for u in users.values():
        for t in u.tx:
            if t.is_trial:
                trials[t.product] += 1
                if any(p.product == t.product and not p.is_trial and p.purchased_at >= t.purchased_at for p in u.tx):
                    converted[t.product] += 1
    print("\ntrial to paid by product")
    for product, n in trials.most_common():
        print(f"  {product:14} trials {n:6,}  converted {converted[product]:5,}  rate {converted[product] / n:6.1%}")
    last = Counter(u.install_at.date() for u in users.values())
    print("\ninstalls per day, last 10 days")
    for day in sorted(last)[-10:]:
        print(f"  {day}  {last[day]:5,}")


# ----------------------------------------------------------------------------- build


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def build(users: dict[str, User], now: datetime, seed: int, out: Path) -> None:
    """Iteration 1: a manifest-based copy of the captured set. Later iterations replace pieces of it."""
    out.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(CAPTURED.glob("*.json")):
        shutil.copy2(path, out / path.name)
        copied.append(path.name)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clock": now.isoformat(),
        "seed": seed,
        "source": "captured fixtures copied; offline dataset loaded (%d users)" % len(users),
        "tests_list": "ab_tests_list.json",
        "tests": ["ab_test_get_onboarding.json", "ab_test_get_main_na.json", "ab_test_get_settings_completed.json", "ab_test_get_ai_limit_draft.json"],
        "metrics_list": "ab_tests_metrics_list.json",
        "metrics_trees": {"b2c90b2b-59b0-48fc-b821-b90061d1ae1e": {"lifetime": "ab_test_metrics_get_onboarding_lifetime.json",
                                                                  "country": "ab_test_metrics_get_onboarding_by_country.json"}},
        "metrics_totals": {"b2c90b2b-59b0-48fc-b821-b90061d1ae1e": "ab_test_metrics_total_onboarding.json"},
        "flows": "flows_list.json",
        "flow_metrics": "flows_metrics_list.json",
        "placements": "placements_list.json",
        "placement_details": ["placement_get_onboarding.json"],
        "segments": "segments_list.json",
        "products": "products_list.json",
        "winners": {"35299a82-0d41-4b50-a874-bf86e11c33d0": "a7c2595b-2c9b-4dc2-9e30-8ff715e6ecaa"},
        "charts": {"revenue": "analytics_chart_revenue_week_by_product.json"},
        "conversions": {"install-paid": "analytics_conversion_install_paid_by_flow.json", "trial-paid": "analytics_conversion_trial_paid.json"},
    }
    write_json(out / "manifest.json", manifest)
    print(f"wrote {len(copied)} fixtures + manifest to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["analyze", "build"])
    parser.add_argument("--offline", help="folder with users.csv.gz and transactions.csv.gz")
    parser.add_argument("--out", default=str(EXPANDED))
    parser.add_argument("--now", default=DEFAULT_NOW, help="demo clock, ISO 8601 (default %(default)s)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    users = load_offline(find_offline_dir(args.offline))
    if args.command == "analyze":
        analyze(users)
        return
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    build(users, now, args.seed, Path(args.out))


if __name__ == "__main__":
    main()
