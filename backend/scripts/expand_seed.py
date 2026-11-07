#!/usr/bin/env python
"""Generate the expanded demo fixture set from the hackathon's offline Lumen dataset.

The captured fixtures (backend/referee/adapty/fixtures) are real Adapty answers for one day of traffic.
This script rebuilds the same API answers from the 50,000-user offline dataset that seeded Lumen
(adapty-seed-data-hack/data/offline, copied to backend/scripts/data), so the mock store can serve
weeks of attributed traffic, per-day series and more tests. Nothing here talks to Adapty.

Usage (from backend/):
    python -X utf8 scripts/expand_seed.py analyze                      # what the offline data holds
    python -X utf8 scripts/expand_seed.py build [--now ISO] [--seed N]  # write fixtures_expanded/

The dataset is shifted in time so its last install lands on the demo clock (--now). Deterministic:
same inputs, same clock, same seed -> identical files.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
CAPTURED = BACKEND / "referee" / "adapty" / "fixtures"
EXPANDED = BACKEND / "referee" / "adapty" / "fixtures_expanded"
DEFAULT_OFFLINE = [BACKEND / "scripts" / "data", REPO.parent / "adapty-seed-data-hack" / "data" / "offline"]
DEFAULT_NOW = "2026-11-07T17:00:00Z"
DEFAULT_SEED = 20261107
PROCEEDS_RATIO = 0.781   # proceeds / gross revenue seen in the captured Lumen answers
NET_RATIO = 0.713        # net proceeds / gross revenue
BOOTSTRAP_DRAWS = 20000

sys.path.insert(0, str(BACKEND))

from referee.catalog import Catalog  # noqa: E402
from referee.stats.proportions import two_proportion_z_test  # noqa: E402

# ----------------------------------------------------------------------------- offline dataset


@dataclass
class Tx:
    user_id: str
    seq: int
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


def iso(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if value else None


def iso_day(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT00:00:00.000000+0000")


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
                user_id=row["user_id"], seq=int(row["seq"]), product=row["product"], store_product_id=row["store_product_id"],
                purchased_at=_dt(row["purchased_at"]) or user.install_at, expires_at=_dt(row["expires_at"]),
                price_usd=float(row["price_usd"] or 0.0), is_trial=row["offer"] == "free_trial", refunded_at=_dt(row["refunded_at"]),
            ))
    for user in users.values():
        user.tx.sort(key=lambda t: (t.purchased_at, t.seq))
    return users


def shift_to_clock(users: dict[str, User], clock: datetime) -> timedelta:
    """Move every timestamp so the newest install happens at the demo clock."""
    newest = max(u.install_at for u in users.values())
    shift = clock - newest
    for u in users.values():
        u.install_at += shift
        for t in u.tx:
            t.purchased_at += shift
            if t.expires_at:
                t.expires_at += shift
            if t.refunded_at:
                t.refunded_at += shift
    return shift


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
            print(f"  {flow:14} users {n:6,}  payers {payers[test][flow]:5,}  revenue ${revenue[test][flow]:10,.0f}  rpv ${revenue[test][flow] / n:6.2f}")
    trials: Counter = Counter()
    converted: Counter = Counter()
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


# ----------------------------------------------------------------------------- scenario


@dataclass(frozen=True)
class ArmSpec:
    flow_key: str
    weight: int
    title: str
    # Synthetic tests draw their viewers from users of an existing flow (source_flow_key), optionally one shard of them.
    source_flow_key: str | None = None
    shard: tuple[int, int] = (0, 1)


@dataclass(frozen=True)
class TestSpec:
    test_id: str
    title: str
    goal: str
    placement_key: str
    segment_key: str | None
    arms: tuple[ArmSpec, ...]
    state: str
    started_days_ago: float | None
    stopped_days_ago: float | None = None
    winner_flow_key: str | None = None
    source_title: str | None = None  # the ab_test value in the offline dataset
    created_days_ago: float | None = None
    # Segments that have their own audience on the placement take those users first (Adapty audience priority).
    exclude_segments: tuple[str, ...] = ()


FLOW_NAMES = {
    "onb_trial": "Onboarding - Annual trial", "onb_weekly": "Onboarding - Weekly first", "main": "Main - 3 plans",
    "main_lifetime": "Main - Lifetime anchor", "ai_limit": "AI limit reached - Pro", "settings": "Settings - Upgrade",
    "winback": "Win-back - Monthly",
    # flows that exist only in the expanded set
    "main_social": "Main - Social proof",
    "onb_weekly_eur": "Onboarding - Weekly first (EUR prices)",
}
SYNTHETIC_FLOWS = {"main_social", "onb_weekly_eur"}
SEGMENT_COUNTRIES = {"na": {"US", "CA"}, "eu1": {"GB", "DE", "FR", "NL", "SE"}}
SEGMENT_TITLES = {"na": "US & Canada", "eu1": "Europe Tier-1", "payers": "Payers"}
ONBOARDING_SCREENS = [("scr_welcome", "1. Welcome", 1.0), ("scr_goal", "2. Goal", 0.9), ("scr_paywall", "3. Paywall", 0.8)]
PAYWALL_SCREEN = [("scr_paywall", "Paywall", 1.0)]

SCENARIO: list[TestSpec] = [
    TestSpec("b2c90b2b-59b0-48fc-b821-b90061d1ae1e", "Onboarding: annual trial vs weekly first",
             "Find which onboarding offer maximises 60-day revenue per install", "onboarding", None,
             (ArmSpec("onb_trial", 50, "A"), ArmSpec("onb_weekly", 50, "B")), "live", started_days_ago=9,
             source_title="Onboarding: annual trial vs weekly first", exclude_segments=("eu1",)),
    TestSpec("fa529c42-4d24-4dde-b63a-e15fda1aa93d", "Main: 3 plans vs lifetime anchor (NA)",
             "Does a lifetime anchor lift annual share in North America?", "main", "na",
             (ArmSpec("main", 50, "A"), ArmSpec("main_lifetime", 50, "B")), "live", started_days_ago=9,
             source_title="Main: 3 plans vs lifetime anchor (NA)"),
    TestSpec("35299a82-0d41-4b50-a874-bf86e11c33d0", "Settings: upgrade vs lifetime anchor",
             "Earlier test - stopped with a winner", "settings_upgrade", None,
             (ArmSpec("settings", 50, "A"), ArmSpec("main_lifetime", 50, "B")), "completed", started_days_ago=60,
             stopped_days_ago=30, winner_flow_key="settings", source_title="Settings: upgrade vs lifetime anchor"),
    TestSpec("7c4c06ef-f5da-45a3-9ec1-05d644e78f03", "AI limit: Pro vs 3 plans", "Draft - planned for next sprint",
             "ai_limit_reached", None, (ArmSpec("ai_limit", 50, "A"), ArmSpec("main", 50, "B")), "draft", started_days_ago=None),
    # Synthetic three-arm test: the non-NA users of the main paywall, with the lifetime anchor as control and the
    # 3-plans users split in two shards, one of them relabelled as a new "social proof" flow.
    TestSpec("3a7c1f2e-9b4d-4c6a-8e21-5d0f7b9c4a11", "Main paywall: lifetime anchor vs 3 plans vs social proof",
             "Which main paywall layout maximises revenue per viewer outside North America?", "main", None,
             (ArmSpec("main_lifetime", 34, "A", source_flow_key="main_lifetime"),
              ArmSpec("main", 33, "B", source_flow_key="main", shard=(0, 2)),
              ArmSpec("main_social", 33, "C", source_flow_key="main", shard=(1, 2))),
             "live", started_days_ago=90),
    # Synthetic Europe Tier-1 onboarding test: weekly-first users of the five EU1 countries split in two shards; the
    # second shard is relabelled as a localized-price flow. Same outcome distribution, so the honest answer is "no
    # difference", and after 95 days the sample is a week short of the plan: the WAIT_SAMPLE state.
    TestSpec("6e2b8d41-7f3a-4b9c-a1d5-2c8e9f0b7d33", "Onboarding EU: weekly first vs EUR prices",
             "Do localized EUR prices lift 60-day revenue per install in Europe Tier-1?", "onboarding", "eu1",
             (ArmSpec("onb_weekly", 50, "A", source_flow_key="onb_weekly", shard=(0, 2)),
              ArmSpec("onb_weekly_eur", 50, "B", source_flow_key="onb_weekly", shard=(1, 2))),
             "live", started_days_ago=95),
]


# ----------------------------------------------------------------------------- reference data from the captured answers


class Reference:
    """Ids and names Adapty already assigned to Lumen: flows, placements, segments, products, variations."""

    def __init__(self, rng: random.Random, clock: datetime) -> None:
        self.catalog = Catalog.load()
        self.flows = load_json(CAPTURED / "flows_list.json")["data"]
        self.flow_id_by_name = {f["name"]: f["id"] for f in self.flows}
        for key in sorted(SYNTHETIC_FLOWS):
            name = FLOW_NAMES[key]
            if name not in self.flow_id_by_name:
                flow_id = stable_uuid(rng)
                self.flow_id_by_name[name] = flow_id
                self.flows.append({"id": flow_id, "name": name, "status": "published", "creation_source": "flow_builder",
                                   "updated_at": iso(clock - timedelta(days=91))})
        self.placements = load_json(CAPTURED / "placements_list.json")["data"]
        self.placement_by_key = {p["developer_id"]: p for p in self.placements}
        self.segments = load_json(CAPTURED / "segments_list.json")["data"]
        self.segment_id_by_title = {s["title"]: s["id"] for s in self.segments}
        self.products = load_json(CAPTURED / "products_list.json")["data"]
        self.variation_ids: dict[tuple[str, str], str] = {}
        for name in ("ab_test_get_onboarding.json", "ab_test_get_main_na.json", "ab_test_get_settings_completed.json", "ab_test_get_ai_limit_draft.json"):
            detail = load_json(CAPTURED / name)
            for arm in detail["flows"]:
                self.variation_ids[(detail["ab_test_id"], arm["flow_id"])] = arm["variation_id"]

    def flow_id(self, key: str) -> str:
        return self.flow_id_by_name[FLOW_NAMES[key]]

    def flow_name(self, key: str) -> str:
        return FLOW_NAMES[key]

    def variation_id(self, test_id: str, flow_id: str, rng: random.Random) -> str:
        if (test_id, flow_id) not in self.variation_ids:
            self.variation_ids[(test_id, flow_id)] = stable_uuid(rng)
        return self.variation_ids[(test_id, flow_id)]

    def product_for_key(self, key: str):
        return self.catalog.by_key.get(key)


def stable_uuid(rng: random.Random) -> str:
    return "%08x-%04x-4%03x-%04x-%012x" % (rng.getrandbits(32), rng.getrandbits(16), rng.getrandbits(12),
                                          0x8000 | rng.getrandbits(14), rng.getrandbits(48))


# ----------------------------------------------------------------------------- aggregation


@dataclass
class ArmAgg:
    spec: ArmSpec
    flow_id: str
    variation_id: str
    users: list[User]
    metrics: dict
    user_revenue: list[float]
    by_day: list[dict]
    by_product: dict[str, dict]
    p2bb: float = 0.0
    low: float = 0.0
    mean_per_1000: float = 0.0
    high: float = 0.0
    p_value: float | None = None


def metric_block(users: list[User], since: datetime | None, until: datetime, completion_share: float = 1.0) -> dict:
    """Adapty's metric keys for a set of viewers, counting transactions in (since, until]."""
    views = len(users)
    completions = int(round(views * completion_share))
    paid = []
    trials = []
    refunds = 0
    subscribers: set[str] = set()
    for u in users:
        for t in u.tx:
            if t.purchased_at > until or (since is not None and t.purchased_at <= since):
                continue
            subscribers.add(u.user_id)
            if t.is_trial:
                trials.append((u, t))
            else:
                paid.append(t)
            if t.refunded_at and t.refunded_at <= until and (since is None or t.refunded_at > since):
                refunds += 1
    revenue = sum(t.price_usd for t in paid)
    payers = {t.user_id for t in paid}
    finished = [(u, t) for u, t in trials if t.expires_at and t.expires_at <= until]
    converted = 0
    for u, t in finished:
        if any(p.product == t.product and not p.is_trial and t.purchased_at <= p.purchased_at <= until for p in u.tx):
            converted += 1
    trial_users = {u.user_id for u, _ in trials}
    n_trials = len(trials)
    proceeds = revenue * PROCEEDS_RATIO
    net = revenue * NET_RATIO
    pct = lambda a, b: (a / b * 100.0) if b else 0.0  # noqa: E731
    return {
        "views": views, "unique_profiles_views": views, "total_completions": completions, "total_uniq_completions": completions,
        "from_start_conversion": 100.0 if views else 0.0,
        "revenue": revenue, "proceeds": proceeds, "net_revenue": net,
        "purchases": len(paid), "trials": n_trials, "unique_subscribers": len(subscribers), "unique_paid_subscribers": len(payers),
        "arppu": revenue / len(payers) if payers else 0.0, "arpu": revenue / views if views else 0.0,
        "conversion_rate_purchases": pct(len(paid), views), "conversion_rate_trials": pct(n_trials, views),
        "trials_cancelled": len(finished) - converted, "refunds": refunds,
        "arpas": revenue / len(subscribers) if subscribers else 0.0,
        "apppu": proceeds / len(payers) if payers else 0.0, "appas": proceeds / len(subscribers) if subscribers else 0.0,
        "conversion_rate_refunds": pct(refunds, len(paid)),
        "conversion_rate_purchases_by_users": pct(len(payers), views), "conversion_rate_trials_by_users": pct(len(trial_users), views),
        "conversion_rate_trial_paid": pct(converted, len(finished)),
        "trials_finished": len(finished), "trials_paid": converted,
        "users": views, "installs": views,
        "_active_trials_rate": (n_trials - len(finished)) / n_trials if n_trials else 0.0,
    }


def strip_private(block: dict) -> dict:
    return {k: v for k, v in block.items() if not k.startswith("_")}


def sum_blocks(blocks: list[dict]) -> dict:
    """Root totals: counts add up, rates are recomputed from the sums."""
    total = {k: 0.0 for k in blocks[0] if not k.startswith("_")} if blocks else {}
    count_keys = ("views", "unique_profiles_views", "total_completions", "total_uniq_completions", "revenue", "proceeds", "net_revenue",
                  "purchases", "trials", "unique_subscribers", "unique_paid_subscribers", "trials_cancelled", "refunds",
                  "trials_finished", "trials_paid", "users", "installs")
    for b in blocks:
        for k in count_keys:
            total[k] += b[k]
    for k in ("views", "unique_profiles_views", "total_completions", "total_uniq_completions", "purchases", "trials", "unique_subscribers",
              "unique_paid_subscribers", "trials_cancelled", "refunds", "trials_finished", "trials_paid", "users", "installs"):
        total[k] = int(total[k])
    pct = lambda a, b: (a / b * 100.0) if b else 0.0  # noqa: E731
    v, rev, payers, subs = total["views"], total["revenue"], total["unique_paid_subscribers"], total["unique_subscribers"]
    total.update({
        "from_start_conversion": pct(total["total_completions"], v), "arppu": rev / payers if payers else 0.0, "arpu": rev / v if v else 0.0,
        "conversion_rate_purchases": pct(total["purchases"], v), "conversion_rate_trials": pct(total["trials"], v),
        "arpas": rev / subs if subs else 0.0, "apppu": total["proceeds"] / payers if payers else 0.0, "appas": total["proceeds"] / subs if subs else 0.0,
        "conversion_rate_refunds": pct(total["refunds"], total["purchases"]), "conversion_rate_purchases_by_users": pct(payers, v),
        "conversion_rate_trials_by_users": pct(total["trials"], v), "conversion_rate_trial_paid": pct(total["trials_paid"], total["trials_finished"]),
    })
    return total


def days_between(start: datetime, end: datetime) -> list[datetime]:
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    while day <= end:
        out.append(day)
        day += timedelta(days=1)
    return out


def aggregate_arm(ref: Reference, spec: TestSpec, arm: ArmSpec, users: list[User], start: datetime, end: datetime, rng: random.Random) -> ArmAgg:
    flow_id = ref.flow_id(arm.flow_key)
    block = metric_block(users, None, end)
    user_revenue = [sum(t.price_usd for t in u.tx if not t.is_trial and t.purchased_at <= end) for u in users]
    by_day = []
    for day in days_between(start, end):
        day_end = min(day + timedelta(days=1) - timedelta(microseconds=1), end)
        day_users = [u for u in users if day <= u.install_at <= day_end]
        point = metric_block(day_users, None, end)  # the day's installs, followed to the clock
        tx_block = metric_block(users, day - timedelta(microseconds=1), day_end)  # money moved that day
        point.update({k: tx_block[k] for k in ("revenue", "proceeds", "net_revenue", "purchases", "trials", "refunds", "trials_paid", "trials_finished")})
        point = strip_private(point)
        point["x"] = iso_day(day)
        by_day.append(point)
    by_product: dict[str, dict] = {}
    for product in ref.catalog.products_for_flow(FLOW_NAMES[arm.flow_key]):
        key = next(k for k, p in ref.catalog.by_key.items() if p.product_id == product.product_id)
        paid = [t for u in users for t in u.tx if t.product == key and not t.is_trial and t.purchased_at <= end]
        trials = [t for u in users for t in u.tx if t.product == key and t.is_trial and t.purchased_at <= end]
        by_product[product.product_id] = {"title": product.title, "purchases": len(paid), "trials": len(trials),
                                          "revenue": sum(t.price_usd for t in paid), "payers": len({t.user_id for t in paid})}
    return ArmAgg(arm, flow_id, ref.variation_id(spec.test_id, flow_id, rng), users, block, user_revenue, by_day, by_product)


def bayesian_fields(arms: list[ArmAgg], rng: random.Random) -> None:
    """P2BB and the 99% range per 1,000 viewers from a normal approximation of each arm's revenue per viewer."""
    stats = []
    for a in arms:
        n = len(a.user_revenue)
        mean = sum(a.user_revenue) / n if n else 0.0
        var = sum((r - mean) ** 2 for r in a.user_revenue) / (n - 1) if n > 1 else 0.0
        stats.append((mean, math.sqrt(var / n) if n else 0.0))
    if all(m == 0.0 for m, _ in stats):
        share = 100.0 / len(arms) if arms else 0.0
        for a in arms:
            a.p2bb, a.low, a.mean_per_1000, a.high = share, 0.0, 0.0, 0.0
        return
    wins = [0] * len(arms)
    draws: list[list[float]] = [[] for _ in arms]
    for _ in range(BOOTSTRAP_DRAWS):
        sample = [max(0.0, rng.gauss(m, s)) if s > 0 else m for m, s in stats]
        wins[max(range(len(arms)), key=lambda i: sample[i])] += 1
        for i, value in enumerate(sample):
            draws[i].append(value)
    for i, a in enumerate(arms):
        a.p2bb = wins[i] / BOOTSTRAP_DRAWS * 100.0
        ordered = sorted(draws[i])
        mean_per_1000 = stats[i][0] * 1000.0
        if a.metrics["unique_paid_subscribers"] >= 50:
            a.low = ordered[int(0.005 * BOOTSTRAP_DRAWS)] * 1000.0
            a.high = ordered[int(0.995 * BOOTSTRAP_DRAWS) - 1] * 1000.0
            a.mean_per_1000 = mean_per_1000
        elif a.metrics["unique_paid_subscribers"] > 0:
            a.low, a.mean_per_1000, a.high = 0.0, mean_per_1000, 2.0 * mean_per_1000
        else:
            a.low, a.mean_per_1000, a.high = 0.0, 0.0, 0.0
    if len(arms) == 2 and all(a.metrics["views"] > 0 for a in arms):
        p = two_proportion_z_test(arms[0].metrics["unique_paid_subscribers"], arms[0].metrics["views"],
                                  arms[1].metrics["unique_paid_subscribers"], arms[1].metrics["views"]).p_value
        for a in arms:
            a.p_value = p


def arm_row(a: ArmAgg, with_title: bool = False, with_active: bool = False) -> dict:
    row = strip_private(a.metrics)
    if with_title:
        row["title"] = a.spec.title
    row.update({"variation_id": a.variation_id, "flow_id": a.flow_id, "weight": a.spec.weight})
    if with_active:
        row["active_trials_rate"] = a.metrics["_active_trials_rate"]
    row.update({"low_boundary": a.low, "average_per_1000": a.mean_per_1000, "upper_boundary": a.high,
                "probability": a.p2bb, "p_value": a.p_value})
    return row


def screen_nodes(ref: Reference, a: ArmAgg, end: datetime) -> list[dict]:
    screens = ONBOARDING_SCREENS if a.spec.flow_key.startswith("onb_") else PAYWALL_SCREEN
    nodes = []
    for screen_id, title, share in screens:
        node = strip_private(metric_block(a.users, None, end, completion_share=share))
        views = int(round(a.metrics["views"] * share))
        node.update({"views": views, "unique_profiles_views": views, "total_completions": views, "total_uniq_completions": views,
                     "from_start_conversion": share * 100.0, "level": "screen", "title": title, "screen_id": screen_id, "values": [], "items": []})
        if screen_id != "scr_paywall":
            for k in ("revenue", "proceeds", "net_revenue", "purchases", "trials", "unique_subscribers", "unique_paid_subscribers",
                      "arppu", "arpu", "conversion_rate_purchases", "conversion_rate_trials", "trials_cancelled", "refunds", "arpas",
                      "apppu", "appas", "conversion_rate_refunds", "conversion_rate_purchases_by_users", "conversion_rate_trials_by_users",
                      "conversion_rate_trial_paid", "trials_finished", "trials_paid"):
                node[k] = 0
        else:
            for product_id, p in a.by_product.items():
                child = {k: 0 for k in strip_private(a.metrics)}
                child.update({"views": views, "unique_profiles_views": views, "total_completions": views, "total_uniq_completions": views,
                              "from_start_conversion": share * 100.0, "purchases": p["purchases"], "trials": p["trials"],
                              "revenue": p["revenue"], "proceeds": p["revenue"] * PROCEEDS_RATIO, "net_revenue": p["revenue"] * NET_RATIO,
                              "unique_paid_subscribers": p["payers"], "arpu": p["revenue"] / views if views else 0.0,
                              "level": "product", "title": p["title"], "product_id": product_id, "values": [], "items": []})
                node["items"].append(child)
        nodes.append(node)
    return nodes


# ----------------------------------------------------------------------------- build


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def user_shard(user: User, count: int) -> int:
    return int(user.user_id.lstrip("u") or "0") % count


def test_users(users: dict[str, User], spec: TestSpec, start: datetime | None, end: datetime) -> dict[str, list[User]]:
    """Viewers per arm. Real tests take the dataset's own assignment; synthetic tests take users of the placement who
    were in no test, matched by source flow and shard."""
    by_flow: dict[str, list[User]] = {arm.flow_key: [] for arm in spec.arms}
    if start is None:
        return by_flow
    excluded = set().union(*(SEGMENT_COUNTRIES[s] for s in spec.exclude_segments)) if spec.exclude_segments else set()
    wanted = SEGMENT_COUNTRIES[spec.segment_key] if spec.segment_key in SEGMENT_COUNTRIES else None

    def in_audience(u: User) -> bool:
        if u.country in excluded or not (start <= u.install_at <= end):
            return False
        return wanted is None or u.country in wanted

    if spec.source_title is not None:
        for u in users.values():
            if u.ab_test == spec.source_title and u.flow in by_flow and in_audience(u):
                by_flow[u.flow].append(u)
    else:
        for arm in spec.arms:
            source = arm.source_flow_key or arm.flow_key
            index, count = arm.shard
            for u in users.values():
                if (u.placement == spec.placement_key and u.flow == source and user_shard(u, count) == index
                        and (u.ab_test is None or wanted is not None) and in_audience(u)):
                    by_flow[arm.flow_key].append(u)
    for bucket in by_flow.values():
        bucket.sort(key=lambda u: u.install_at)
    return by_flow


def build(users: dict[str, User], clock: datetime, seed: int, out: Path) -> None:
    rng = random.Random(seed)
    ref = Reference(rng, clock)
    shift = shift_to_clock(users, clock)
    synthetic_flow_users: dict[str, list[User]] = {}
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.json"):
        stale.unlink()

    listed: list[dict] = []
    manifest: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "clock": clock.isoformat(), "seed": seed,
        "source": f"offline Lumen dataset ({len(users):,} users) shifted by {shift.days} days so its last install lands on the clock",
        "tests_list": "ab_tests_list.json", "tests": [], "metrics_list": "ab_tests_metrics_list.json", "metrics_trees": {},
        "metrics_totals": {}, "flows": "flows_list.json", "flow_metrics": "flows_metrics_list.json", "placements": "placements_list.json",
        "placement_details": [], "segments": "segments_list.json", "products": "products_list.json",
        "winners": {}, "charts": {"revenue": "analytics_chart_revenue_week_by_product.json"},
        "conversions": {"install-paid": "analytics_conversion_install_paid_by_flow.json", "trial-paid": "analytics_conversion_trial_paid.json"},
    }
    metrics_rows: list[dict] = []
    summary: list[str] = []

    for spec in SCENARIO:
        started = clock - timedelta(days=spec.started_days_ago) if spec.started_days_ago is not None else None
        stopped = clock - timedelta(days=spec.stopped_days_ago) if spec.stopped_days_ago is not None else None
        end = stopped or clock
        created = started or (clock - timedelta(days=spec.created_days_ago or 1))
        placement = ref.placement_by_key[spec.placement_key]
        segment_ids = [ref.segment_id_by_title[SEGMENT_TITLES[spec.segment_key]]] if spec.segment_key else []
        arms_users = test_users(users, spec, started, end)
        for arm in spec.arms:
            if arm.flow_key in SYNTHETIC_FLOWS:
                synthetic_flow_users.setdefault(arm.flow_key, []).extend(arms_users[arm.flow_key])
        arms = [aggregate_arm(ref, spec, arm, arms_users[arm.flow_key], started or end, end, rng) for arm in spec.arms]
        if spec.state != "draft":
            bayesian_fields(arms, rng)
        row = {"ab_test_id": spec.test_id, "title": spec.title, "type": "flow", "state": spec.state,
               "placement": {"placement_id": placement["id"], "title": placement["title"]}, "segment_ids": segment_ids, "priority": 0,
               "started_at": iso(started), "stopped_at": iso(stopped)}
        listed.append(row)
        detail = {**row, "goal": spec.goal, "paywalls": [],
                  "flows": [{"flow_id": a.flow_id, "flow_name": FLOW_NAMES[a.spec.flow_key], "weight": a.spec.weight, "title": a.spec.title,
                             "variation_id": a.variation_id} for a in arms],
                  "created_at": iso(created)}
        detail_name = f"ab_test_get_{spec.test_id}.json"
        write_json(out / detail_name, detail)
        manifest["tests"].append(detail_name)
        if spec.winner_flow_key:
            manifest["winners"][spec.test_id] = ref.flow_id(spec.winner_flow_key)
        if spec.state == "draft":
            summary.append(f"{spec.title}: draft, no traffic")
            continue
        root = sum_blocks([a.metrics for a in arms])
        metrics_rows.append({**root, "ab_test_id": spec.test_id, "items": [arm_row(a) for a in arms]})
        total = {"data": {"metrics": [arm_row(a, with_title=True, with_active=True) for a in arms],
                          "ab_test": {"ab_test_id": spec.test_id, "title": spec.title, "goal": spec.goal,
                                      "paywalls_group": {"paywalls_group_id": stable_uuid(rng), "title": spec.title}, "vars": {}, "created_at": iso(created)},
                          "state": spec.state, "started_at": iso(started), "stopped_at": iso(stopped),
                          "active_trials_rate": (sum(a.metrics["trials"] * a.metrics["_active_trials_rate"] for a in arms) / max(1, root["trials"]))}}
        total_name = f"ab_test_metrics_total_{spec.test_id}.json"
        write_json(out / total_name, total)
        manifest["metrics_totals"][spec.test_id] = total_name
        tree_root = {**root, "level": "root", "title": spec.title, "values": [], "items": []}
        for a in arms:
            node = arm_row(a)
            node.update({"level": "variation", "title": a.spec.title, "values": a.by_day, "items": screen_nodes(ref, a, end)})
            tree_root["items"].append(node)
        tree_name = f"ab_test_metrics_tree_{spec.test_id}_lifetime.json"
        write_json(out / tree_name, {"data": tree_root})
        manifest["metrics_trees"][spec.test_id] = {"lifetime": tree_name}
        summary.append(f"{spec.title}: {spec.state}, " + ", ".join(
            f"{a.spec.title} {a.metrics['views']} viewers / {a.metrics['unique_paid_subscribers']} payers / ${a.metrics['revenue']:,.0f} / P2BB {a.p2bb:.0f}% / open trials {a.metrics['trials'] - a.metrics['trials_finished']}"
            for a in arms))

    write_json(out / "ab_tests_list.json", {"data": listed, "meta": {"pagination": {"count": len(listed), "page": 1, "pages": 1}}})
    write_json(out / "ab_tests_metrics_list.json", {"data": metrics_rows})

    # flows and their lifetime metrics across every placement
    flow_rows = []
    for key, name in FLOW_NAMES.items():
        if key in SYNTHETIC_FLOWS:
            flow_users = synthetic_flow_users.get(key, [])
        else:
            flow_users = [u for u in users.values() if u.flow == key and u.install_at <= clock]
        block = strip_private(metric_block(flow_users, None, clock))
        block["flow_id"] = ref.flow_id(key)
        flow_rows.append(block)
    write_json(out / "flows_metrics_list.json", {"data": flow_rows})
    write_json(out / "flows_list.json", {"data": ref.flows, "meta": {"pagination": {"count": len(ref.flows), "page": 1, "pages": 1}}})
    for name in ("placements_list.json", "segments_list.json", "products_list.json",
                 "analytics_chart_revenue_week_by_product.json", "analytics_conversion_install_paid_by_flow.json", "analytics_conversion_trial_paid.json"):
        shutil.copy2(CAPTURED / name, out / name)
    write_json(out / "manifest.json", manifest)
    print(f"wrote {len(list(out.glob('*.json')))} files to {out}  (clock {clock.isoformat()}, shift {shift.days} days)")
    for line in summary:
        print(" ", line)


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
    clock = datetime.fromisoformat(args.now.replace("Z", "+00:00"))
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    build(users, clock, args.seed, Path(args.out))


if __name__ == "__main__":
    main()
