# Adapty developer API notes (for the mock frontend)

Captured 7 Nov 2026 from the Adapty CLI 0.18.0 source (`npm root -g`/adapty/dist) and live calls against the
seeded Lumen app. The dashboard page you pointed at (https://app.adapty.io/ab-tests/flows) is rendered from the
same backend family; the CLI help literally describes `ab-tests metrics get` as "the dashboard results page".
Use this API, not the dashboard's private calls: it is documented, token-authenticated, and the judges built it.

Folder contents

| Path | What |
|---|---|
| `fixtures/*.json` | Real responses from the Lumen app (no secrets inside). Serve them to the frontend. |
| `mock_api.py` | Stdlib HTTP server that answers the real routes with the fixtures, CORS on. `python mock_api.py --self-test` checks it. |
| `refresh_fixtures.sh` | Re-captures the fixtures with the CLI (needs `adapty auth login`). |

## 1. Transport

| Item | Value |
|---|---|
| Base URL | `https://api-admin.adapty.io/api/v1/developer` (env `ADAPTY_API_URL` overrides) |
| Auth | `Authorization: Bearer <developer token>` |
| Token source | env `ADAPTY_TOKEN`, else `%LOCALAPPDATA%\adapty\config.json` -> `access_token` (written by `adapty auth login`, OAuth device flow). Never commit it. |
| Headers | `accept: application/json`; `content-type: application/json` on bodies; optional `user-agent`, `x-adapty-interactive: true|false`, `adapty-tz: Europe/Belgrade` (metrics `get` period points only) |
| Paths | Every path ends with a trailing slash (`/apps/<id>/ab-tests/`). Only `/migrations` does not. |
| Pagination | `page[number]`, `page[size]`; list answers are `{ "data": [...], "meta": { "pagination": { "count", "page", "pages" } } }` |
| Errors | JSON body with a code and message; 401 = token expired, run `adapty auth login`; 429 carries `Retry-After` |
| Rate limits | Analytics: 2 requests/s per app, 360/min for all callers. Metrics routes are rate limited per app. The CLI never retries metrics or analytics POSTs. |
| Other hosts | Attribution `https://api-ua.adapty.io/api/v1/cli`, Apple Search Ads `https://api-asa-admin.adapty.io/api/v1/cli` (same bearer token) |

Quick check from a shell (token read from the CLI config, never printed):

```bash
TOKEN=$(python -c "import json,os;print(json.load(open(os.path.join(os.environ['LOCALAPPDATA'],'adapty','config.json')))['access_token'])")
curl -s -H "Authorization: Bearer $TOKEN" -H "accept: application/json" \
  "https://api-admin.adapty.io/api/v1/developer/apps/9c35cea9-1655-4af3-9f05-ac16f383e91d/ab-tests/?type=flow"
```

Browser frontends cannot call this host directly: the token would ship to the client and CORS will block it.
Serve the fixtures (mock_api.py) for the demo, and put a tiny backend proxy in front of the real API if you go live.

## 2. A/B tests `/apps/{app_id}/ab-tests/`

| Method and path | Query / body | Fixture |
|---|---|---|
| `GET .../ab-tests/` | `type=flow|paywall`, `filter[state]=live|draft|completed|inactive|archived`, `filter[placement_id]=a,b`, `filter[segment_id]=...`, `filter[search]=...`, `page[number]`, `page[size]` | `ab_tests_list.json` |
| `GET .../ab-tests/{id}/` | | `ab_test_get_*.json` |
| `POST .../ab-tests/` | `{ "title", "goal"?, "placement_id"?, "segment_ids"?: [one id], "flows": [{ "flow_id", "weight", "title"? }] }` or `"paywalls": [{ "paywall_id", "weight", "title"? }]` (exactly one of the two). Creates a draft. | |
| `PUT .../ab-tests/{id}/` | same body, whole test re-sent; a live test accepts only title and goal changes | |
| `POST .../ab-tests/{id}/start/` | `{ "placement_id", "segment_ids": [] }` (empty = All users). Only drafts start. | |
| `POST .../ab-tests/{id}/stop/` | `{}` (no content) or `{ "winner_flow_id" }` or `{ "another_flow_id_to_run" }`; paywall tests use `winner_paywall_id` / `another_paywall_id_to_run`. `{}` is refused on All users. | |
| `POST .../ab-tests/{id}/replace/` | create body with `placement_id` required; answers the new test, the old one becomes completed ("Modify" in the dashboard) | |
| `DELETE .../ab-tests/{id}/` | archives; refused while live | |

Test object (list item plus `goal`, `paywalls`, `flows` on `get`):

```json
{
  "ab_test_id": "b2c90b2b-59b0-48fc-b821-b90061d1ae1e",
  "title": "Onboarding: annual trial vs weekly first",
  "type": "flow",
  "state": "live",
  "placement": { "placement_id": "2d81af2b-6159-4416-924b-e3d927e468e5", "title": "Onboarding" },
  "segment_ids": [],
  "priority": 0,
  "started_at": "2026-11-07T04:07:55.077750Z",
  "stopped_at": null,
  "goal": "Find which onboarding offer maximises 60-day revenue per install",
  "paywalls": [],
  "flows": [
    { "flow_id": "1f573a07-...", "flow_name": "Onboarding - Annual trial", "weight": 50, "title": "A", "variation_id": "168c021e-..." },
    { "flow_id": "00ac93b0-...", "flow_name": "Onboarding - Weekly first",  "weight": 50, "title": "B", "variation_id": "7c0f5a55-..." }
  ]
}
```

### 2.1 Metrics (what the dashboard results page shows)

| Method and path | Query / body | Fixture |
|---|---|---|
| `GET .../ab-tests/metrics/` | `type=flow`, `filter[ab_test_id]=id1,id2` -> lifetime numbers, one row per test with `items` = arms | `ab_tests_metrics_list.json` |
| `POST .../ab-tests/{id}/metrics/?type=flow` | body: `{ "filters": { "date": ["2026-09-01","2026-10-21"], "country"?: ["US"], "store"?: ["app_store"] }, "period_unit"?: "day|week|month", "date_type"?: "purchase_date|profile_install_date", "segmentation_by"?: "country|store" }`; header `adapty-tz`. A flow test with no date = lifetime. Paywall tests require date, date range and date_type. | `ab_test_metrics_get_onboarding_lifetime.json`, `ab_test_metrics_get_onboarding_by_country.json` |
| `GET .../ab-tests/{id}/metrics/total/?type=flow` | arms over the whole life, plus the test header and `active_trials_rate` | `ab_test_metrics_total_onboarding.json` |
| `GET .../ab-tests/{id}/metrics/values/?type=flow` | the filter values the test accepts | |

Tree shape of `POST .../metrics/` (flow test): `data` is the root node, `data.items[]` are arms (`level: "variation"`),
each arm has `values[]` (period points when `period_unit` is set), and `items[]` children: with `segmentation_by`
they are `level: "segment"` nodes (`segmentation: "US"`, `title: "United States"`); without it they are
`level: "screen"` nodes (`screen_id`, `position`, `is_paywall`) whose `items[]` are `level: "product"` nodes
(`product_id`, `title`, `plan_share`).

Every node carries the same 27 metrics plus `users` and `installs`:

| Group | Fields |
|---|---|
| Traffic | `views`, `unique_profiles_views`, `total_completions`, `total_uniq_completions`, `from_start_conversion` (% of viewers who reached this node) |
| Money | `revenue`, `proceeds` (after store commission), `net_revenue` (after taxes), `arppu`, `arpu`, `arpas`, `apppu`, `appas` |
| Counts | `purchases`, `trials`, `unique_subscribers`, `unique_paid_subscribers`, `trials_cancelled`, `trials_finished`, `trials_paid`, `refunds` |
| Rates (%) | `conversion_rate_purchases`, `conversion_rate_trials`, `conversion_rate_refunds`, `conversion_rate_purchases_by_users`, `conversion_rate_trials_by_users`, `conversion_rate_trial_paid` |

Arm-only fields, the ones the referee needs:

| Field | Meaning |
|---|---|
| `weight` | traffic split in percent |
| `probability` | P2BB in percent: the chance the arm is best by revenue per viewer. 0 on every arm = not computed. |
| `low_boundary`, `average_per_1000`, `upper_boundary` | 99% range of revenue per 1,000 unique viewers. Under 50 payers the server sends 0 / mean / 2 x mean. |
| `p_value` | only for a flow test with exactly two arms; `null` otherwise. In `metrics get` the per-period P2BB is the value of that period for flow tests, a running total for paywall tests; the leader lives in `metrics total`. |
| `active_trials_rate` | only in `metrics total`; 1 in the seeded tests (every trial still active) |
| `variation_id`, `flow_id` (or `paywall_id`) | ids to join with `ab-tests get` and `flows list` |

Live numbers today (`ab_tests_metrics_list.json`): Onboarding 285 vs 254 views, 35 vs 0 purchases, P2BB 100 / 0,
p 7.7e-9. Main NA 37 vs 40 views, 1 purchase each, P2BB 66.84 / 33.16, p 0.955. Settings 34 vs 41 views, 0 purchases,
P2BB 50 / 50, p null.

## 3. Flows, placements, paywalls, segments, products

| Resource | Endpoints |
|---|---|
| Flows | `GET /apps/{app}/flows/` (`id`, `name`, `status`, `creation_source`, `updated_at`), `GET /flows/{id}/`, `POST /flows/` (row only), `GET|PUT /flows/{id}/config/` (Flow Builder JSON, ~150 KB, see `flow_config_onb_trial.json`), `POST /flows/{id}/config/validate/`, `POST /flows/{id}/publish/` (async: poll `status` for `published` or `publication_failed`), `POST /flows/media/images/` (multipart) |
| Flow metrics | `GET /apps/{app}/flows/metrics/?filter[flow_id]=a,b` -> `[{ flow_id, views, purchases, trials, revenue, refunds, unique_paid_subscribers }]` (`flows_metrics_list.json`); `POST /flows/{id}/metrics/` same body as the A/B metrics; `GET /flows/{id}/metrics/values/` |
| Placements | `GET /apps/{app}/placements/` (`id`, `developer_id`, `title`, `type: flow|paywall`, `is_active`), `GET /placements/{id}/` adds `audiences[]`, `POST /placements/`, `PUT /placements/{id}/` body `{ "title", "developer_id", "audiences": [...] }` |
| Placement audiences | each entry: `{ "content_type": "flow" | "paywall" | "flow_ab_test" | "ab_test" | "flow_cross_ab_test" | "cross_ab_test", "segment_ids": [], "priority": 0, "flow_id"? | "paywall_id"? | "ab_test_id"? }`. Writing a placement without its running test entry stops that test. |
| Placement metrics | `GET /apps/{app}/placements/metrics/?type=flow&filter[placement_id]=...`, `POST /placements/{id}/metrics/?type=flow`, values |
| Paywalls | `GET|POST /apps/{app}/paywalls/`, `GET|PUT /paywalls/{id}/`, `GET /paywalls/{id}/placements/`, metrics like flows |
| Segments | `GET /apps/{app}/segments/` (`id`, `title`, `description`), `GET|PUT /segments/{id}/`, `POST /segments/` body `{ "title", "description"?, "filters": [{ "field_name", "operator", "value_list" }] }` (CLI shorthand `field:OPERATOR:value`, e.g. `ip_country:IN:US,CA`, `total_revenue_usd:>:0`, `install_date:>=:2026-01-01`) |
| Products | `GET /apps/{app}/products/` (`id`, `title`, `period`, `access_level_id`, `price_usd`, `offers_count`, `vendor_products.app_store|play_store { id, product_id, base_plan_id, store_status }`), `/access-levels/`, `/apps/`, `/me/` |

## 4. Analytics `/apps/{app_id}/analytics/`

| Method and path | Body | Fixture |
|---|---|---|
| `GET .../analytics/catalog/` | | run `adapty analytics catalog --app <id>` |
| `POST .../analytics/metrics/` | `{ "chart_id": "revenue|mrr|arr|arppu|arpu|installs|subscriptions_active|subscriptions_new|subscriptions_expired|trials_new|trials_active|refund_events|refund_money|billing_issue|grace_period|...", "filters": { "date": [from, to], "compare_date"?: [from, to], "<dimension>"?: [values] }, "period_unit"?: "day|week|month|quarter|year", "segmentation"?: "country|store_product_id|flow_id|placement_id|segment_id|attribution_channel|...", "revenue_basis"?: "gross|proceeds|net", "timezone"? }` | `analytics_chart_revenue_week_by_product.json` |
| `POST .../analytics/conversion/` | `{ "conversion_id": "install-paid|install-trial|view-trial|view-paid|trial-paid|paid-2period|...|billing-issue-paid|grace-period-paid", "filters", "period_unit"?, "segmentation"? }` | `analytics_conversion_install_paid_by_flow.json`, `analytics_conversion_trial_paid.json` |
| `POST .../analytics/cohort/`, `funnel/`, `ltv/`, `retention/` | same query envelope, see `adapty analytics <op> --help` | |
| `GET .../analytics/values/?dimension=country` | the values a filter accepts | |

Answer envelope: `{ "data": { "value", "compare", "segments": [{ "key", "title", "is_total", "value", "values": [{ "x": "2026-07-01T00:00:00.000000+0000", "value" }] }] }, "meta": { "query", "definitions": { "value", "revenue_basis", "freshness" } } }`.
Conversions add `value_from`, `value_to` (and `has_unfinished`, `value_from_unfinished` per point). Dimension values are
`{ "key": "00000000-0000-0000-0000-000000000000", "title": "No Data" }` for history that is not attributed to a flow.
Freshness note from the API: events reach analytics at least 15 minutes after Adapty receives them.

## 5. Lumen ids (live app)

| Thing | Id |
|---|---|
| App | `9c35cea9-1655-4af3-9f05-ac16f383e91d` |
| Test, Onboarding: annual trial vs weekly first (live, all users) | `b2c90b2b-59b0-48fc-b821-b90061d1ae1e` on placement `2d81af2b-6159-4416-924b-e3d927e468e5`; arms A `1f573a07-f8e0-4800-aced-8838977f8246` (variation `168c021e-...`), B `00ac93b0-487c-46a3-a72c-748fc64feadc` (variation `7c0f5a55-...`) |
| Test, Main: 3 plans vs lifetime anchor (NA) (live, segment) | `fa529c42-4d24-4dde-b63a-e15fda1aa93d` on placement `f495d564-fa96-4c0c-a52f-19a4ee7ee4eb`, segment `70d12a72-e25b-4fc2-bd5a-817c27cfa397`; arms `63861760-...` (Main - 3 plans), `ed8bf97b-...` (Main - Lifetime anchor) |
| Test, Settings: upgrade vs lifetime anchor (completed) | `35299a82-0d41-4b50-a874-bf86e11c33d0` on placement `89eb1d46-d64f-4dec-b72f-97f348c0f19c`; arms `a7c2595b-...` (Settings - Upgrade), `ed8bf97b-...` |
| Test, AI limit: Pro vs 3 plans (draft) | `7c4c06ef-f5da-45a3-9ec1-05d644e78f03` on placement `0dfdf0d2-f36a-4b02-9b85-a654ecc3182e`; arms `8d8103e8-...` (AI limit reached - Pro), `63861760-...` |
| Placements | onboarding `2d81af2b-6159-4416-924b-e3d927e468e5`, main `f495d564-fa96-4c0c-a52f-19a4ee7ee4eb`, ai_limit_reached `0dfdf0d2-f36a-4b02-9b85-a654ecc3182e`, settings_upgrade `89eb1d46-d64f-4dec-b72f-97f348c0f19c`, win_back `75dae32c-b1a6-415b-a87b-834819e08a80` |
| Flows | Onboarding - Annual trial `1f573a07-f8e0-4800-aced-8838977f8246`, Onboarding - Weekly first `00ac93b0-487c-46a3-a72c-748fc64feadc`, Main - 3 plans `63861760-06be-4776-8185-5e53536cc72d`, Main - Lifetime anchor `ed8bf97b-8da6-46e4-a47d-fb9e52610baf`, AI limit reached - Pro `8d8103e8-f849-48ad-8a57-2cea40fe82d6`, Settings - Upgrade `a7c2595b-2c9b-4dc2-9e30-8ff715e6ecaa`, Win-back - Monthly `16f65c46-6a6a-4ad8-81ab-14e5a4ae03bf` |
| Products | Weekly (3-day trial) `0334d3e2-b118-48fe-a19d-99b0ad49c36b`, Monthly `44fc7422-5c58-4e40-8f48-bd3df0c0ddb8`, Annual `4fc247e0-2643-44cc-841e-5247981656cd`, Annual (7-day trial) `ed2c0f9d-4935-4c3b-901b-93c5b942bfff`, Lifetime `2e73350f-ad79-4035-b951-2c2a177716b5`, Pro Annual `7e2aff3a-25ce-4576-a40f-484f8fdd1e17` |
| Segments | see `fixtures/segments_list.json` (US & Canada is `70d12a72-...`, used by the NA test) |

Dashboard links for "open in Adapty" buttons: list `https://app.adapty.io/ab-tests/flows`; flow preview under
`https://app.adapty.io/flows/`. Open a test in the dashboard once and copy its URL pattern for deep links.

## 6. Things that bite

- Only today's ~1,000 replayed users are attributed to flows and tests. The four months of history show in
  revenue, MRR, cohorts and products, and as "No Data" when grouped by `flow_id`. Full-history arm outcomes exist
  only in the offline CSV (`adapty-seed-data-hack/data/offline`).
- `probability` is Adapty's Bayesian P2BB. Do not recompute it; add decidability and time to decision on top.
- `p_value` is `null` for three or more arms and for paywall tests.
- Under 50 payers the range is `0 / mean / 2 x mean`; show "not enough payers" instead of plotting it.
- Metrics and analytics POSTs are heavy and rate limited per app. Cache in the backend; poll at most every few minutes.
- Never re-seed the Lumen app, never send transactions. Profile attribute writes go through the server-side API
  (`https://api.adapty.io/api/v2/server-side-api`, secret key), not this developer API.
- Keep the developer token out of the repo and out of the browser. `.env` is in `.gitignore` from the first commit.

## 7. Using it

Mock, for the frontend:

```bash
python mock_api.py                 # http://localhost:8787/apps/<app>/ab-tests/?type=flow
python mock_api.py --self-test     # proves the routes answer
```

Live, from a backend (either of these):

```bash
adapty ab-tests metrics list --app $APP --type flow --ids <id1>,<id2> --json   # subprocess, parse stdout
ADAPTY_TOKEN=... curl -s -H "Authorization: Bearer $ADAPTY_TOKEN" "$BASE/apps/$APP/ab-tests/metrics/?type=flow&filter[ab_test_id]=<id1>,<id2>"
```

Refresh the fixtures after the state changes (a test started, a day of traffic):

```bash
bash refresh_fixtures.sh            # uses the logged-in CLI; APP env overrides the app id
```
