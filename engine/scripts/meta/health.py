#!/usr/bin/env python3
"""Delivery health for a Meta ad account: the facts a results export does not show.

    uv run python engine/scripts/meta/health.py
    uv run python engine/scripts/meta/health.py --days 10 --json
    uv run python engine/scripts/meta/health.py --batch fernwood/ads/statics/test-x-2026-10-08

Read only. Reports:
  - account status now and its most recent status change;
  - dark stretches: runs of 3 or more account hours with no spend at all
    (billing holds, rejections, budget caps), with total hours lost;
  - per live ad set: hours that actually spent, first spend, 7 day spend,
    frequency, CTR and CPC;
  - ads in live campaigns that are rejected, have issues, wait on billing, or
    sit PAUSED in an ad set that has not spent in the window.

Judge tests on hours live, not calendar days: a day with a billing hold or a
rejection is not a test day. --batch reads the campaign ID from that batch's
meta-launch.json and limits the report to it. Credentials: META_ACCESS_TOKEN
and META_AD_ACCOUNT_ID from the environment or the repo-root .env.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brands import REPO_ROOT  # noqa: E402
from graph import Graph, GraphError, credentials, redact  # noqa: E402

BAD = {"DISAPPROVED", "WITH_ISSUES", "PENDING_BILLING_INFO"}
ACCOUNT_STATUS = {
    1: "ACTIVE",
    2: "DISABLED",
    3: "UNSETTLED (payment needed, no delivery)",
    7: "PENDING_RISK_REVIEW",
    8: "PENDING_SETTLEMENT",
    9: "IN_GRACE_PERIOD",
    100: "PENDING_CLOSURE",
    101: "CLOSED",
}
HOUR_FIELD = "hourly_stats_aggregated_by_advertiser_time_zone"


def dark_stretches(spent: set[tuple[str, int]], first: datetime, last: datetime, min_hours: int = 3) -> list[tuple[datetime, int]]:
    """Runs of at least min_hours account hours with no spend, between first and last (account local time)."""
    out: list[tuple[datetime, int]] = []
    run_start, n, t = None, 0, first
    while t <= last:
        if (t.date().isoformat(), t.hour) in spent:
            if n >= min_hours:
                out.append((run_start, n))
            run_start, n = None, 0
        else:
            run_start, n = run_start or t, n + 1
        t += timedelta(hours=1)
    if n >= min_hours:
        out.append((run_start, n))
    return out


def campaign_from_batch(batch: Path) -> str:
    path = batch if batch.is_absolute() else Path.cwd() / batch
    if not path.is_dir():
        path = REPO_ROOT / batch
    state_path = path / "meta-launch.json"
    if not state_path.exists():
        raise SystemExit(f"Error: no meta-launch.json in {path}; launch the batch with --live first")
    campaign_id = json.loads(state_path.read_text()).get("campaign", {}).get("id")
    if not campaign_id:
        raise SystemExit(f"Error: {state_path} records no campaign ID")
    return campaign_id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="window for hourly delivery (default 7)")
    ap.add_argument("--batch", type=Path, help="limit to the campaign recorded in this batch's meta-launch.json")
    ap.add_argument("--campaign", help="limit to one campaign ID")
    ap.add_argument("--json", action="store_true", help="machine readable output")
    a = ap.parse_args()

    creds = credentials(("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"))
    graph = Graph(creds["META_ACCESS_TOKEN"], timeout=60)
    acct = creds["META_AD_ACCOUNT_ID"]
    campaign_id = a.campaign or (campaign_from_batch(a.batch) if a.batch else None)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=a.days)
    info = graph.get(acct, fields="account_status,timezone_name,currency")
    status = ACCOUNT_STATUS.get(info["account_status"], str(info["account_status"]))
    currency = info.get("currency", "")

    # Meta's hourly buckets are in the ad account's time zone.
    tz = ZoneInfo(info.get("timezone_name") or "UTC")
    local_now = now.astimezone(tz).replace(minute=0, second=0, microsecond=0, tzinfo=None)
    window = {"since": since.astimezone(tz).date().isoformat(), "until": local_now.date().isoformat()}

    live = [{"field": "campaign.effective_status", "operator": "IN", "value": ["ACTIVE"]}]
    if campaign_id:
        live.append({"field": "campaign.id", "operator": "EQUAL", "value": campaign_id})

    acct_hours = graph.paged(f"{acct}/insights", level="account", limit=1000, fields="spend",
                             time_range=window, time_increment=1, breakdowns=HOUR_FIELD)
    spent = {(r["date_start"], int(r[HOUR_FIELD][:2])) for r in acct_hours if float(r.get("spend") or 0) > 0}
    if spent:
        first_day = min(d for d, _ in spent)
        first_hour = min(h for d, h in spent if d == first_day)
        first = datetime.fromisoformat(first_day) + timedelta(hours=first_hour)
    else:
        first = local_now
    dark = dark_stretches(spent, first, local_now)
    lost = sum(n for _, n in dark)

    # Most recent status change only: the activities feed is too noisy to page reliably.
    acts = graph.get(f"{acct}/activities", fields="event_time,event_type,extra_data", limit=100).get("data", [])
    flip = next((x for x in acts if x.get("event_type") == "ad_account_update_status"), None)
    if flip:
        try:
            new_value = json.loads(flip.get("extra_data") or "{}").get("new_value")
        except ValueError:
            new_value = "?"
        last_flip = f"{new_value} since {flip['event_time'][:16]} UTC"
    else:
        last_flip = "no status change in the latest 100 events"

    rows = graph.paged(f"{acct}/insights", level="adset", limit=500,
                       fields="campaign_name,adset_id,adset_name,spend",
                       time_range=window, time_increment=1, breakdowns=HOUR_FIELD, filtering=live)
    hours: dict[str, set] = defaultdict(set)
    names: dict[str, dict] = {}
    for r in rows:
        if float(r.get("spend") or 0) > 0:
            hours[r["adset_id"]].add((r["date_start"], r[HOUR_FIELD][:2]))
        names[r["adset_id"]] = {"campaign": r["campaign_name"], "adset": r["adset_name"]}
    totals = {x["adset_id"]: x for x in graph.paged(
        f"{acct}/insights", level="adset", limit=500, date_preset="last_7d",
        fields="adset_id,spend,frequency,ctr,cpc,clicks,impressions", filtering=live)}

    ads = graph.paged(f"{acct}/ads", limit=500,
                      fields="name,effective_status,adset_id,campaign{name},adset{name},ad_review_feedback,issues_info",
                      filtering=live)
    problem_ads = []
    for ad in ads:
        st = ad["effective_status"]
        stuck = st == "PAUSED" and ad["adset_id"] not in hours
        if st in BAD or stuck:
            feedback = (ad.get("ad_review_feedback") or {}).get("global") or {}
            issues = [i.get("error_summary") or i.get("error_message") or "" for i in ad.get("issues_info") or []]
            reason = "; ".join([*feedback.keys(), *filter(None, issues)])
            if stuck and not reason:
                reason = "paused, and its ad set has not spent in the window"
            problem_ads.append({"campaign": ad["campaign"]["name"], "adset": ad["adset"]["name"],
                                "ad": ad["name"], "ad_id": ad["id"], "status": st, "reason": reason})

    sets = []
    for sid, n in names.items():
        hs = hours.get(sid, set())
        t = totals.get(sid, {})
        sets.append({**n, "adset_id": sid, "live_hours": len(hs), "first_spend": min((d for d, _ in hs), default=None),
                     "spend_7d": float(t.get("spend") or 0), "freq_7d": float(t.get("frequency") or 0),
                     "ctr": float(t.get("ctr") or 0), "cpc": float(t.get("cpc") or 0)})
    sets.sort(key=lambda s: (s["campaign"], -s["spend_7d"]))

    out = {
        "account_status": status, "currency": currency, "timezone": info.get("timezone_name"),
        "checked_at": now.isoformat(timespec="minutes"), "campaign_filter": campaign_id,
        "last_status_change": last_flip,
        "dark_stretches": [{"from_local": s.isoformat(timespec="minutes"), "hours": n} for s, n in dark],
        "hours_dark": lost, "hours_since_first_spend": int((local_now - first).total_seconds() // 3600) + 1,
        "adsets": sets, "problem_ads": problem_ads,
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return

    print(f"Account: {status}  (checked {out['checked_at']} UTC, times in {out['timezone']}, {currency})")
    if campaign_id:
        print(f"Campaign filter: {campaign_id} (dark stretches are account wide)")
    print(f"Last status change: {last_flip}")
    print(f"Dark (no spend at all, runs of 3h+): {lost}h of {out['hours_since_first_spend']}h since {first:%d %b %H:00} local")
    for w in out["dark_stretches"]:
        print(f"  {w['from_local']} for {w['hours']}h")
    print(f"\nLive ad sets (hours that spent, last {a.days}d; spend and rates last 7d):")
    current = None
    for s in sets:
        if s["campaign"] != current:
            current = s["campaign"]
            print(f"  {current}")
        print(f"    {s['adset'][:32]:32} {s['live_hours']:>4}h live since {s['first_spend'] or 'never'}"
              f"  {s['spend_7d']:.2f} {currency}  freq {s['freq_7d']:.2f}  CTR {s['ctr']:.2f}%  CPC {s['cpc']:.2f}")
    if not sets:
        print("  none (no active campaigns spent in the window)")
    print(f"\nProblem ads in live campaigns ({len(problem_ads)}):")
    for p in problem_ads:
        print(f"  {p['status']:20} {p['campaign']} / {p['adset']} / {p['ad']} ({p['ad_id']})  {p['reason']}")


if __name__ == "__main__":
    try:
        main()
    except GraphError as e:
        sys.exit(redact(f"Meta error: {e}"))
