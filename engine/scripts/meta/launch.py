#!/usr/bin/env python3
"""Launch a generated static batch to Meta as one campaign.

    uv run python engine/scripts/meta/launch.py --brand fernwood --batch fernwood/ads/statics/test-x-2026-10-08
    uv run python engine/scripts/meta/launch.py ... --live            # create everything PAUSED
    uv run python engine/scripts/meta/launch.py ... --live --enable   # also set it ACTIVE (starts spend)

Dry run is the default: it prints the full plan and makes no network calls.

Structure, from a launcher that has run real batches:
  - one campaign per batch, daily budget on the campaign (CBO), highest volume bidding;
  - one ad set per concept (the manifest's ad_set_key), identical settings and
    targeting on every ad set, so the concept is the only thing that differs;
  - one ad per manifest entry, up to 3 per ad set (the "3" of 3:2:2);
  - each ad is a single image asset_feed_spec creative: the 1x1 image in feeds,
    the 9x16 image in Stories and Reels, every Advantage+ creative enhancement
    off, so the copy runs exactly as written.

Config comes from {brand}/meta.toml (see engine/template/meta.toml). Credentials
come only from META_ACCESS_TOKEN, META_AD_ACCOUNT_ID, META_PAGE_ID and the
optional META_INSTAGRAM_ACTOR_ID, read from the environment or the repo-root .env.

Created IDs are written to meta-launch.json in the batch folder after every
object, so a rerun (or a run stopped by a rate limit) skips what already exists.
Existing objects are never edited. After a live run the brand's
testing/creative-tracker.csv gets one row per ad (status testing).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brands import REPO_ROOT, brand_dir  # noqa: E402
from graph import (  # noqa: E402
    GRAPH_VERSION,
    Graph,
    GraphError,
    credential_status,
    credentials,
    redact,
)

ADS_PER_SET = 3
STATE_FILE = "meta-launch.json"
TRACKER_CHANNEL = "meta-paid"
TRACKER_HEADER = [
    "batch", "date", "concept", "testing-method", "sub-avatar", "core-avatar", "angle",
    "product", "offer", "variation", "messaging-concept", "visual-format", "format",
    "channel", "asset-ref", "status", "result", "notes",
]

OBJECTIVES = {
    # objective: default optimization goal
    "OUTCOME_TRAFFIC": "LINK_CLICKS",
    "OUTCOME_SALES": "OFFSITE_CONVERSIONS",
    "OUTCOME_LEADS": "OFFSITE_CONVERSIONS",
}
CTA_TYPES = {
    "SHOP_NOW", "LEARN_MORE", "SIGN_UP", "ORDER_NOW", "GET_OFFER", "BUY_NOW",
    "SUBSCRIBE", "DOWNLOAD", "BOOK_TRAVEL", "CONTACT_US", "APPLY_NOW", "GET_QUOTE",
}
# Ad sets that reach these countries must name a DSA beneficiary and payor.
DSA_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE",
    "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}
# Every creative_features_spec key Meta documented as of Sep 2026; all opted out.
CREATIVE_FEATURES = [
    "adapt_to_placement", "add_text_overlay", "creative_stickers", "description_automation",
    "enhance_cta", "image_animation", "image_background_gen", "image_brightness_and_contrast",
    "image_templates", "image_text_translation", "image_touchups", "image_uncrop",
    "inline_comment", "media_type_automation", "pac_relaxation", "product_extensions",
    "reveal_details_over_time", "text_optimizations", "text_translation", "translate_voiceover",
    "video_auto_crop", "video_filtering", "video_uncrop",
]
FEED_POSITIONS = {
    "facebook": ["feed", "marketplace", "profile_feed", "right_hand_column", "search"],
    "instagram": ["stream", "explore", "profile_feed"],
}
VERTICAL_POSITIONS = {
    "facebook": ["story", "facebook_reels"],
    "instagram": ["story", "reels"],
}
PLACEHOLDER = re.compile(r"(?<!\{)\{(brand|batch|concept|ad|sub_avatar|angle|offer)\}(?!\})")


# --- config ---------------------------------------------------------------


def load_config(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Error: no Meta config at {path}. Copy engine/template/meta.toml there and fill it in.")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []
    campaign = cfg.get("campaign", {})
    adset = cfg.get("adset", {})
    targeting = cfg.get("targeting", {})
    landing = cfg.get("landing", {})
    creative = cfg.get("creative", {})
    placements = cfg.get("placements", {})

    objective = campaign.get("objective")
    if objective not in OBJECTIVES:
        errors.append(f"campaign.objective must be one of {sorted(OBJECTIVES)}, got {objective!r}")
    budget = campaign.get("daily_budget")
    if not isinstance(budget, int) or budget <= 0:
        errors.append("campaign.daily_budget must be a positive integer in minor units (5000 = 50.00)")
    goal = adset.get("optimization_goal") or OBJECTIVES.get(objective or "", "")
    if goal == "OFFSITE_CONVERSIONS" and not (adset.get("pixel_id") and (adset.get("conversion_event") or adset.get("custom_conversion_id"))):
        errors.append("adset.pixel_id and one of adset.conversion_event or adset.custom_conversion_id are required to optimise for conversions")
    if adset.get("custom_conversion_id") and not str(adset["custom_conversion_id"]).isdigit():
        errors.append("adset.custom_conversion_id must be the numeric id of a custom conversion")
    if not targeting.get("countries"):
        errors.append("targeting.countries must list at least one country code")
    age_min, age_max = targeting.get("age_min", 18), targeting.get("age_max", 65)
    if not (13 <= age_min <= age_max <= 65):
        errors.append(f"targeting ages must satisfy 13 <= age_min <= age_max <= 65, got {age_min} to {age_max}")
    if set(targeting.get("countries", [])) & DSA_COUNTRIES:
        dsa = cfg.get("dsa", {})
        if not (dsa.get("beneficiary") and dsa.get("payor")):
            errors.append("targeting reaches the EU, so dsa.beneficiary and dsa.payor are required")
    url = landing.get("url", "")
    if not url.startswith("https://"):
        errors.append("landing.url must be an https URL")
    for offer, offer_url in landing.get("by_offer", {}).items():
        if not str(offer_url).startswith("https://"):
            errors.append(f"landing.by_offer.{offer} must be an https URL")
    cta = creative.get("cta", "LEARN_MORE")
    if cta not in CTA_TYPES:
        errors.append(f"creative.cta {cta!r} is not one of {sorted(CTA_TYPES)}")
    mode = placements.get("mode", "advantage")
    if mode not in {"advantage", "manual"}:
        errors.append("placements.mode must be 'advantage' or 'manual'")
    if mode == "manual" and not placements.get("publisher_platforms"):
        errors.append("placements.publisher_platforms is required when placements.mode is 'manual'")
    return errors


def fill(template: str, values: dict[str, str]) -> str:
    """Replace {batch}-style placeholders, leaving Meta's {{ad.id}} macros alone."""
    return PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), template)


# --- manifest and plan ------------------------------------------------------


@dataclass
class AdPlan:
    key: str  # manifest copy_file, unique per ad
    number: int
    name: str
    entry: dict
    square: Path
    vertical: Path | None
    link: str
    offer: str


@dataclass
class AdSetPlan:
    key: str  # manifest ad_set_key
    concept: str
    name: str
    ads: list[AdPlan] = field(default_factory=list)


@dataclass
class Plan:
    brand: str
    batch: str
    batch_dir: Path
    campaign_name: str
    adsets: list[AdSetPlan]
    skipped: list[tuple[str, str]]


def angle_offer(brand_root: Path, entry: dict) -> str:
    """The angle file's `offer` frontmatter, or "" when the file or field is missing."""
    path = brand_root / "avatars" / str(entry.get("core_avatar", "")) / str(entry.get("sub_avatar", "")) / f"angle-{entry.get('angle_slug', '')}.md"
    if not path.exists():
        return ""
    match = re.search(r"^offer:\s*[\"']?([^\"'#\n]+?)[\"']?\s*(#.*)?$", path.read_text(), re.M)
    offer = match.group(1).strip() if match else ""
    return "" if offer.startswith("{") else offer


def build_plan(brand: str, brand_root: Path, batch_dir: Path, cfg: dict, allowed: set[str]) -> Plan:
    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Error: no manifest.json in {batch_dir}")
    entries = json.loads(manifest_path.read_text())
    batch = batch_dir.name

    # Concept numbers follow first appearance in the full manifest, so they stay
    # stable when a rerun selects a different subset.
    order: list[str] = []
    for entry in entries:
        if entry.get("ad_set_key") not in order:
            order.append(entry.get("ad_set_key"))

    landing = cfg.get("landing", {})
    utm = landing.get("utm", "")
    adsets: dict[str, AdSetPlan] = {}
    skipped: list[tuple[str, str]] = []
    for entry in entries:
        label = str(entry.get("copy_file") or entry.get("sequence"))
        status = entry.get("review_status", "")
        if status not in allowed:
            skipped.append((label, f"review_status {status or 'missing'} (allowed: {', '.join(sorted(allowed))})"))
            continue
        if not entry.get("headline") or not entry.get("primary_text"):
            skipped.append((label, "missing headline or primary_text"))
            continue
        images = entry.get("image_files") or {}
        square = batch_dir / images["1x1"] if images.get("1x1") else None
        if not square or not square.exists():
            skipped.append((label, f"1x1 image missing ({images.get('1x1') or 'not in manifest'})"))
            continue
        vertical = batch_dir / images["9x16"] if images.get("9x16") else None
        if vertical and not vertical.exists():
            skipped.append((label, f"9x16 image listed but missing ({images['9x16']})"))
            continue

        set_key = entry["ad_set_key"]
        if set_key not in adsets:
            concept = f"c{order.index(set_key) + 1:02d}-{entry.get('angle_slug') or set_key}"
            adsets[set_key] = AdSetPlan(key=set_key, concept=concept, name=f"{batch}//{concept}")
        adset = adsets[set_key]
        if len(adset.ads) >= ADS_PER_SET:
            skipped.append((label, f"ad set {adset.concept} already has {ADS_PER_SET} ads"))
            continue

        number = len(adset.ads) + 1
        offer = angle_offer(brand_root, entry)
        values = {
            "brand": brand,
            "batch": batch,
            "concept": adset.concept,
            "ad": f"{adset.concept}_v{number}",
            "sub_avatar": str(entry.get("sub_avatar", "")),
            "angle": str(entry.get("angle_slug", "")),
            "offer": offer,
        }
        base = landing.get("by_offer", {}).get(offer) or landing["url"]
        query = fill(utm, values)
        link = f"{base}{'&' if '?' in base else '?'}{query}" if query else base
        name = f"{batch}_{adset.concept}_{entry.get('visual_format', 'image')}_{entry.get('messaging_concept', 'copy')}_Image_V{number}"
        adset.ads.append(AdPlan(label, number, name, entry, square, vertical, link, offer))

    campaign_name = fill(cfg.get("campaign", {}).get("name", "{brand} // {batch}"), {"brand": brand, "batch": batch})
    return Plan(brand, batch, batch_dir, campaign_name, list(adsets.values()), skipped)


# --- payloads (pure, so the dry run prints exactly what live sends) ----------


def campaign_payload(cfg: dict, plan: Plan) -> dict:
    campaign = cfg["campaign"]
    return {
        "name": plan.campaign_name,
        "objective": campaign["objective"],
        "buying_type": "AUCTION",
        "status": "PAUSED",
        "special_ad_categories": campaign.get("special_ad_categories", []),
        "daily_budget": campaign["daily_budget"],
        "bid_strategy": campaign.get("bid_strategy", "LOWEST_COST_WITHOUT_CAP"),
    }


def targeting_spec(cfg: dict) -> dict:
    t = cfg["targeting"]
    spec: dict[str, object] = {
        "geo_locations": {
            "countries": t["countries"],
            "location_types": t.get("location_types", ["home", "recent"]),
        },
        "age_min": t.get("age_min", 18),
        "age_max": t.get("age_max", 65),
        "targeting_automation": {"advantage_audience": 1 if t.get("advantage_audience") else 0},
    }
    if t.get("genders"):
        spec["genders"] = t["genders"]
    if t.get("custom_audiences"):
        spec["custom_audiences"] = [{"id": str(i)} for i in t["custom_audiences"]]
    if t.get("excluded_custom_audiences"):
        spec["excluded_custom_audiences"] = [{"id": str(i)} for i in t["excluded_custom_audiences"]]
    placements = cfg.get("placements", {})
    if placements.get("mode") == "manual":
        spec["publisher_platforms"] = placements["publisher_platforms"]
        for key in ("facebook_positions", "instagram_positions"):
            if placements.get(key):
                spec[key] = placements[key]
    return spec


def adset_payload(cfg: dict, adset: AdSetPlan, campaign_id: str) -> dict:
    a = cfg.get("adset", {})
    goal = a.get("optimization_goal") or OBJECTIVES[cfg["campaign"]["objective"]]
    payload: dict[str, object] = {
        "name": adset.name,
        "campaign_id": campaign_id,
        "status": "PAUSED",
        "billing_event": a.get("billing_event", "IMPRESSIONS"),
        "optimization_goal": goal,
        "destination_type": "WEBSITE",
        "targeting": targeting_spec(cfg),
    }
    if goal == "OFFSITE_CONVERSIONS":
        # A custom event (such as a server event sent through the Conversions API) is optimised through a custom conversion.
        if a.get("custom_conversion_id"):
            payload["promoted_object"] = {"pixel_id": str(a["pixel_id"]), "custom_event_type": "OTHER",
                                          "custom_conversion_id": str(a["custom_conversion_id"])}
        else:
            payload["promoted_object"] = {"pixel_id": str(a["pixel_id"]), "custom_event_type": a["conversion_event"]}
        # Meta allows only a 1 day window on LINK_CLICKS sets, so this is conversions only.
        payload["attribution_spec"] = [{"event_type": "CLICK_THROUGH", "window_days": a.get("attribution_window_days", 7)}]
    dsa = cfg.get("dsa", {})
    if dsa.get("beneficiary"):
        payload["dsa_beneficiary"] = dsa["beneficiary"]
        payload["dsa_payor"] = dsa.get("payor") or dsa["beneficiary"]
    return payload


def placement_rules(cfg: dict) -> list[dict]:
    """Square in feeds, vertical in Stories and Reels, trimmed to manual placements if set."""
    placements = cfg.get("placements", {})
    platforms = ["facebook", "instagram"] if cfg.get("_instagram") else ["facebook"]
    manual = placements.get("mode") == "manual"
    if manual:
        platforms = [p for p in platforms if p in placements.get("publisher_platforms", [])]
    rules = []
    for label, positions in (("square", FEED_POSITIONS), ("vertical", VERTICAL_POSITIONS)):
        spec: dict[str, object] = {"publisher_platforms": platforms}
        for platform in platforms:
            wanted = positions[platform]
            if manual and placements.get(f"{platform}_positions"):
                wanted = [p for p in wanted if p in placements[f"{platform}_positions"]]
            if wanted:
                spec[f"{platform}_positions"] = wanted
        if any(k.endswith("_positions") for k in spec):
            rules.append({"customization_spec": spec, "image_label": {"name": label}})
    return rules


def creative_payload(cfg: dict, ad: AdPlan, page_id: str, ig_id: str, square_hash: str, vertical_hash: str | None) -> dict:
    creative_cfg = cfg.get("creative", {})
    cta = creative_cfg.get("cta", "LEARN_MORE")
    description = creative_cfg.get("description", "")
    story: dict[str, object] = {"page_id": page_id}
    if ig_id:
        story["instagram_user_id"] = ig_id
    payload: dict[str, object] = {"name": ad.name, "object_story_spec": story}
    rules = placement_rules({**cfg, "_instagram": bool(ig_id)}) if vertical_hash else []
    if vertical_hash and len(rules) == 2:
        feed: dict[str, object] = {
            "ad_formats": ["SINGLE_IMAGE"],
            "optimization_type": "PLACEMENT",
            "images": [
                {"hash": square_hash, "adlabels": [{"name": "square"}]},
                {"hash": vertical_hash, "adlabels": [{"name": "vertical"}]},
            ],
            "bodies": [{"text": ad.entry["primary_text"]}],
            "titles": [{"text": ad.entry["headline"]}],
            "link_urls": [{"website_url": ad.link}],
            "call_to_action_types": [cta],
            "asset_customization_rules": rules,
        }
        if description:
            feed["descriptions"] = [{"text": description}]
        payload["asset_feed_spec"] = feed
    else:
        # No usable 9x16: a plain single image link ad, square everywhere.
        link_data: dict[str, object] = {
            "link": ad.link,
            "message": ad.entry["primary_text"],
            "name": ad.entry["headline"],
            "image_hash": square_hash,
            "call_to_action": {"type": cta, "value": {"link": ad.link}},
        }
        if description:
            link_data["description"] = description
        story["link_data"] = link_data
    if creative_cfg.get("url_tags"):
        payload["url_tags"] = creative_cfg["url_tags"]
    payload["degrees_of_freedom_spec"] = {
        "creative_features_spec": {f: {"enroll_status": "OPT_OUT"} for f in CREATIVE_FEATURES}
    }
    return payload


def ad_payload(cfg: dict, ad: AdPlan, adset_id: str, creative_id: str) -> dict:
    payload: dict[str, object] = {
        "name": ad.name,
        "adset_id": adset_id,
        "creative": {"creative_id": creative_id},
        "status": "PAUSED",
    }
    pixel = cfg.get("adset", {}).get("pixel_id")
    if pixel:
        payload["tracking_specs"] = [{"action.type": ["offsite_conversion"], "fb_pixel": [str(pixel)]}]
    return payload


# --- state ------------------------------------------------------------------


def load_state(batch_dir: Path) -> dict:
    path = batch_dir / STATE_FILE
    state = json.loads(path.read_text()) if path.exists() else {}
    state.setdefault("adsets", {})
    state.setdefault("images", {})
    state.setdefault("ads", {})
    return state


def save_state(batch_dir: Path, state: dict) -> None:
    state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (batch_dir / STATE_FILE).write_text(json.dumps(state, indent=2) + "\n")


# --- output -----------------------------------------------------------------


def money(minor: int, currency: str) -> str:
    return f"{minor / 100:.2f} {currency}".strip()


def first_line(text: str, width: int = 90) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line if len(line) <= width else line[: width - 3] + "..."


def print_plan(plan: Plan, cfg: dict, state: dict, mode: str, show_payloads: bool) -> None:
    c = cfg["campaign"]
    t = cfg["targeting"]
    currency = c.get("currency", "")
    n_ads = sum(len(s.ads) for s in plan.adsets)
    print(f"Meta launch plan ({mode}), Graph {GRAPH_VERSION}")
    print(f"  brand     {plan.brand}")
    print(f"  batch     {plan.batch}  ({plan.batch_dir})")
    print("  creds     " + "  ".join(f"{k}={v}" for k, v in credential_status().items()))
    print()
    existing = state.get("campaign", {}).get("id")
    print(f"Campaign  {plan.campaign_name}" + (f"  [exists {existing}]" if existing else "  [new, PAUSED]"))
    print(f"  objective {c['objective']}  budget {money(c['daily_budget'], currency)}/day on the campaign (CBO)  bid {c.get('bid_strategy', 'LOWEST_COST_WITHOUT_CAP')}")
    goal = cfg.get("adset", {}).get("optimization_goal") or OBJECTIVES[c["objective"]]
    if goal == "OFFSITE_CONVERSIONS":
        a = cfg.get("adset", {})
        target = f"custom conversion {a['custom_conversion_id']}" if a.get("custom_conversion_id") else a.get("conversion_event")
        goal = f"{goal} on {target}"
    print(f"  ad sets   optimise {goal},countries {','.join(t['countries'])}, age {t.get('age_min', 18)} to {t.get('age_max', 65)}, "
          f"placements {cfg.get('placements', {}).get('mode', 'advantage')}, advantage audience {'on' if t.get('advantage_audience') else 'off'}")
    if t.get("custom_audiences") or t.get("excluded_custom_audiences"):
        print(f"  audiences include {t.get('custom_audiences', [])} exclude {t.get('excluded_custom_audiences', [])}")
    dsa = cfg.get("dsa", {})
    if dsa.get("beneficiary"):
        print(f"  dsa       beneficiary {dsa['beneficiary']}, payor {dsa.get('payor') or dsa['beneficiary']}")
    print(f"  cta       {cfg.get('creative', {}).get('cta', 'LEARN_MORE')}  url_tags {cfg.get('creative', {}).get('url_tags', '(none)')}")
    print(f"\n{len(plan.adsets)} ad set(s), {n_ads} ad(s)")
    for adset in plan.adsets:
        set_id = state["adsets"].get(adset.key, {}).get("id")
        short = f"  (short of {ADS_PER_SET}; build what exists, do not invent)" if len(adset.ads) < ADS_PER_SET else ""
        print(f"\n  Ad set {adset.name}" + (f"  [exists {set_id}]" if set_id else "  [new, PAUSED]") + short)
        print(f"    concept key {adset.key}")
        for ad in adset.ads:
            ad_id = state["ads"].get(ad.key, {}).get("ad_id")
            print(f"    Ad V{ad.number} {ad.name}" + (f"  [exists {ad_id}]" if ad_id else "  [new, PAUSED]"))
            e = ad.entry
            print(f"      angle     {e.get('sub_avatar')} / {e.get('angle_slug')}  offer {ad.offer or '(none)'}")
            print(f"      headline  {e['headline']}")
            print(f"      primary   {first_line(e['primary_text'])}")
            images = ad.square.name + (f" + {ad.vertical.name}" if ad.vertical else "  (no 9x16: square everywhere)")
            print(f"      images    {images}")
            print(f"      link      {ad.link}")
    if plan.skipped:
        print(f"\nSkipped {len(plan.skipped)} manifest entr{'y' if len(plan.skipped) == 1 else 'ies'}:")
        for label, reason in plan.skipped:
            print(f"  {label}: {reason}")
    if show_payloads:
        page, ig = "<META_PAGE_ID>", "<META_INSTAGRAM_ACTOR_ID>" if credential_status()["META_INSTAGRAM_ACTOR_ID"] == "set" else ""
        print("\nPayloads (IDs and hashes are placeholders until live):")
        print(json.dumps({"campaign": campaign_payload(cfg, plan)}, indent=2))
        for adset in plan.adsets:
            print(json.dumps({"adset": adset_payload(cfg, adset, "<campaign_id>")}, indent=2))
            for ad in adset.ads:
                vertical = f"<hash:{ad.vertical.name}>" if ad.vertical else None
                print(json.dumps({"creative": creative_payload(cfg, ad, page, ig, f"<hash:{ad.square.name}>", vertical)}, indent=2))
                print(json.dumps({"ad": ad_payload(cfg, ad, "<adset_id>", "<creative_id>")}, indent=2))


# --- live -------------------------------------------------------------------


def upload_image(graph: Graph, account: str, path: Path, state: dict, batch_dir: Path) -> str:
    if path.name in state["images"]:
        return state["images"][path.name]
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    result = graph.post(f"{account}/adimages", {}, files={path.name: (path.name, path.read_bytes(), mime)})
    images = result.get("images") or {}
    entry = images.get(path.name) or next(iter(images.values()), {})
    if not entry.get("hash"):
        raise GraphError(f"adimages returned no hash for {path.name}")
    state["images"][path.name] = entry["hash"]
    save_state(batch_dir, state)
    print(f"  uploaded {path.name}")
    return entry["hash"]


def run_live(plan: Plan, cfg: dict, state: dict, enable: bool) -> None:
    creds = credentials(("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID"))
    graph = Graph(creds["META_ACCESS_TOKEN"])
    account, page_id, ig_id = creds["META_AD_ACCOUNT_ID"], creds["META_PAGE_ID"], creds["META_INSTAGRAM_ACTOR_ID"]

    info = graph.get(account, fields="name,currency,account_status,timezone_name")
    page = graph.get(page_id, fields="name")
    print(f"\naccount {info.get('name')} ({account}) currency {info.get('currency')} status {info.get('account_status')} tz {info.get('timezone_name')}")
    print(f"page    {page.get('name')} ({page_id})  instagram {'set' if ig_id else 'not set'}")
    if info.get("account_status") != 1:
        raise SystemExit(f"Error: ad account status is {info.get('account_status')}, not 1 (ACTIVE); fix billing or review first")
    expected = cfg["campaign"].get("currency")
    if expected and expected != info.get("currency"):
        raise SystemExit(f"Error: meta.toml says currency {expected} but the account bills in {info.get('currency')}; daily_budget would be wrong")
    if state.get("account") and state["account"] != account:
        raise SystemExit(f"Error: {STATE_FILE} was written for {state['account']}, not {account}")
    state["account"] = account
    state["batch"] = plan.batch

    if not state.get("campaign", {}).get("id"):
        created = graph.post(f"{account}/campaigns", campaign_payload(cfg, plan))
        state["campaign"] = {"id": created["id"], "name": plan.campaign_name}
        save_state(plan.batch_dir, state)
        print(f"campaign {created['id']} created PAUSED")
    else:
        print(f"campaign {state['campaign']['id']} exists, not changed")
    campaign_id = state["campaign"]["id"]

    for adset in plan.adsets:
        record = state["adsets"].get(adset.key)
        if not record:
            created = graph.post(f"{account}/adsets", adset_payload(cfg, adset, campaign_id))
            record = {"id": created["id"], "name": adset.name, "concept": adset.concept}
            state["adsets"][adset.key] = record
            save_state(plan.batch_dir, state)
            print(f"ad set {adset.concept} {created['id']} created PAUSED")
        else:
            print(f"ad set {adset.concept} {record['id']} exists, not changed")
        for ad in adset.ads:
            row = state["ads"].get(ad.key, {})
            if row.get("ad_id"):
                print(f"  ad V{ad.number} {row['ad_id']} exists, not changed")
                continue
            if not row.get("creative_id"):
                square = upload_image(graph, account, ad.square, state, plan.batch_dir)
                vertical = upload_image(graph, account, ad.vertical, state, plan.batch_dir) if ad.vertical else None
                creative = graph.post(f"{account}/adcreatives", creative_payload(cfg, ad, page_id, ig_id, square, vertical))
                row = {"creative_id": creative["id"], "adset_key": adset.key, "concept": adset.concept, "name": ad.name, "link": ad.link}
                state["ads"][ad.key] = row
                save_state(plan.batch_dir, state)
            created = graph.post(f"{account}/ads", ad_payload(cfg, ad, record["id"], row["creative_id"]))
            row["ad_id"] = created["id"]
            save_state(plan.batch_dir, state)
            print(f"  ad V{ad.number} {created['id']} created PAUSED (creative {row['creative_id']})")

    if enable:
        graph.post(campaign_id, {"status": "ACTIVE"})
        for adset in plan.adsets:
            graph.post(state["adsets"][adset.key]["id"], {"status": "ACTIVE"})
            for ad in adset.ads:
                graph.post(state["ads"][ad.key]["ad_id"], {"status": "ACTIVE"})
        state["enabled_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        save_state(plan.batch_dir, state)
        print("enabled campaign, ad sets and ads (spend starts once Meta approves the ads)")

    check = graph.get(campaign_id, fields="name,status,effective_status,daily_budget")
    print(f"\ncampaign {check.get('status')}/{check.get('effective_status')} budget {check.get('daily_budget')}")
    for adset in plan.adsets:
        s = graph.get(state["adsets"][adset.key]["id"], fields="status,effective_status")
        print(f"  {adset.concept}: {s.get('status')}/{s.get('effective_status')}")


# --- tracker ----------------------------------------------------------------


def update_tracker(tracker: Path, plan: Plan, state: dict) -> None:
    """Mark each launched ad in the 18-column tracker: update its untested row or append one."""
    if tracker.exists():
        with tracker.open(newline="") as fh:
            rows = list(csv.reader(fh))
        if not rows or rows[0] != TRACKER_HEADER:
            raise SystemExit(f"Error: {tracker} header is not the 18-column format; not touching it")
    else:
        rows = [TRACKER_HEADER]
    col = {name: i for i, name in enumerate(TRACKER_HEADER)}
    date_match = re.search(r"\d{4}-\d{2}-\d{2}$", plan.batch)
    batch_date = date_match.group(0) if date_match else datetime.now().date().isoformat()
    updated = appended = 0

    for adset in plan.adsets:
        for ad in adset.ads:
            ad_id = state["ads"].get(ad.key, {}).get("ad_id")
            if not ad_id or any(r[col["asset-ref"]] == ad_id for r in rows[1:]):
                continue
            e = ad.entry
            match = next(
                (
                    r for r in rows[1:]
                    if r[col["batch"]] == plan.batch
                    and r[col["angle"]] == e.get("angle_slug", "")
                    and r[col["messaging-concept"]] == e.get("messaging_concept", "")
                    and r[col["visual-format"]] == e.get("visual_format", "")
                    and r[col["status"]] == "untested"
                ),
                None,
            )
            if match:
                previous = match[col["asset-ref"]]
                if previous and previous != ad_id:
                    note = f"image {previous}"
                    match[col["notes"]] = f"{match[col['notes']]}; {note}" if match[col["notes"]] else note
                match[col["asset-ref"]] = ad_id
                match[col["channel"]] = TRACKER_CHANNEL
                match[col["status"]] = "testing"
                match[col["concept"]] = match[col["concept"]] or adset.concept
                updated += 1
            else:
                row = [""] * len(TRACKER_HEADER)
                row[col["batch"]] = plan.batch
                row[col["date"]] = batch_date
                row[col["concept"]] = adset.concept
                row[col["testing-method"]] = "discovery"
                row[col["sub-avatar"]] = e.get("sub_avatar", "")
                row[col["core-avatar"]] = e.get("core_avatar", "")
                row[col["angle"]] = e.get("angle_slug", "")
                row[col["offer"]] = ad.offer
                row[col["variation"]] = f"v{ad.number}"
                row[col["messaging-concept"]] = e.get("messaging_concept", "")
                row[col["visual-format"]] = e.get("visual_format", "")
                row[col["format"]] = "static"
                row[col["channel"]] = TRACKER_CHANNEL
                row[col["asset-ref"]] = ad_id
                row[col["status"]] = "testing"
                row[col["notes"]] = f"image {ad.square.name}"
                rows.append(row)
                appended += 1

    tracker.parent.mkdir(parents=True, exist_ok=True)
    with tracker.open("w", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)
    print(f"\ntracker {tracker}: {updated} row(s) updated, {appended} appended")


# --- main -------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", required=True, help="brand folder name at the repo root")
    ap.add_argument("--batch", required=True, type=Path, help="batch folder holding manifest.json")
    ap.add_argument("--config", type=Path, help="Meta config (default {brand}/meta.toml)")
    ap.add_argument("--brand-root", type=Path, help="brand folder outside the repo root (overrides --brand lookup)")
    ap.add_argument("--allow-status", default="passed",
                    help="comma separated manifest review_status values to launch (default: passed)")
    ap.add_argument("--live", action="store_true", help="create everything PAUSED on Meta")
    ap.add_argument("--enable", action="store_true", help="with --live, set campaign, ad sets and ads ACTIVE")
    ap.add_argument("--payloads", action="store_true", help="also print every Graph payload")
    ap.add_argument("--no-tracker", action="store_true", help="do not update creative-tracker.csv after a live run")
    args = ap.parse_args()
    if args.enable and not args.live:
        raise SystemExit("Error: --enable requires --live")

    brand_root = args.brand_root.resolve() if args.brand_root else brand_dir(args.brand)
    batch_dir = (args.batch if args.batch.is_absolute() else Path.cwd() / args.batch).resolve()
    if not batch_dir.is_dir():
        alt = (REPO_ROOT / args.batch).resolve()
        if not alt.is_dir():
            raise SystemExit(f"Error: batch folder {args.batch} not found")
        batch_dir = alt
    cfg = load_config(args.config or brand_root / "meta.toml")
    errors = validate_config(cfg)
    if errors:
        raise SystemExit("Error: meta config is invalid:\n  " + "\n  ".join(errors))

    allowed = {s.strip() for s in args.allow_status.split(",") if s.strip()}
    plan = build_plan(args.brand, brand_root, batch_dir, cfg, allowed)
    state = load_state(batch_dir)
    mode = "LIVE, ENABLE" if args.enable else "LIVE, PAUSED" if args.live else "dry run"
    print_plan(plan, cfg, state, mode, args.payloads)
    if not plan.adsets:
        raise SystemExit("Error: nothing to launch (every manifest entry was skipped)")

    if not args.live:
        print("\nDry run: nothing was sent. --live creates everything PAUSED; --live --enable starts spend.")
        return

    run_live(plan, cfg, state, args.enable)
    if not args.no_tracker:
        update_tracker(brand_root / "testing" / "creative-tracker.csv", plan, state)


if __name__ == "__main__":
    try:
        main()
    except GraphError as exc:
        hint = " (rate limited; state is saved, rerun later to continue)" if exc.rate_limited else " (state is saved; rerun skips what exists)"
        sys.exit(redact(f"Meta error: {exc}{hint}"))
