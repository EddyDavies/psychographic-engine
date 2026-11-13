# Launch and Assess (Agent Workflow)

## When to Use

A generated batch in `{brand}/ads/statics/test-{batch}-{YYYY-MM-DD}/` has passed review and is ready for Meta, or a live batch needs a verdict. Launching and enabling change real spend; every write step below needs an explicit yes from the human in this conversation.

## Read First

1. `engine/method/media-buying.md`: structure, judge timing, kill, hold, promote, scale
2. The batch's test plan (`test-plan-template.md`): KPI, minimum spend, success criteria
3. `{brand}/meta.toml`: objective, budget, targeting, landing URL (template in `engine/template/meta.toml`)
4. `{brand}/testing/creative-tracker.csv`: what already ran
5. The batch's `manifest.json` and, if it exists, `meta-launch.json`

## Launch

1. **Dry run.** Prints the full plan and sends nothing.

   ```bash
   uv run python engine/scripts/meta/launch.py --brand {brand} --batch {brand}/ads/statics/{batch}
   ```

   Add `--payloads` to see every Graph payload.

2. **Review the plan with the human.** Check, and say what you found:
   - Budget: the daily figure in `meta.toml` was approved in writing for this batch. Never pick one.
   - One ad set per concept, up to 3 ads each. Any set marked "short of 3" or any skipped entry is reported, not patched. Never write or edit copy to fill a gap.
   - Every link opens the right landing page and carries the UTMs; the offer matches the angle's `offer`.
   - Targeting is broad (countries, age, no interests) unless the test plan says otherwise; DSA names are present for EU countries.
   - Entries skipped for `review_status` stay out unless the human approved them (then `--allow-status passed,needs_human_review`).

3. **Live, paused.** Only after a yes. Creates the campaign, ad sets, creatives and ads, all PAUSED, and records every ID in `meta-launch.json`.

   ```bash
   uv run python engine/scripts/meta/launch.py --brand {brand} --batch {brand}/ads/statics/{batch} --live
   ```

   A rate limit or error stops the run with state saved; rerun the same command and it skips what exists. The tracker gets one row per ad (`channel` meta-paid, `asset-ref` the ad ID, `status` testing). Ask the human to look at the ads in Ads Manager before spending.

4. **Enable.** Only after a second, separate yes. Sets campaign, ad sets and ads ACTIVE; spend starts once Meta approves the ads.

   ```bash
   uv run python engine/scripts/meta/launch.py --brand {brand} --batch {brand}/ads/statics/{batch} --live --enable
   ```

5. **Close the loop.** Set each launched angle file to `status: testing` with a Test History line (concept id, date). Run `uv run python engine/scripts/check-knowledge.py`.

## Assess

1. **Delivery health first.** Read only.

   ```bash
   uv run python engine/scripts/meta/health.py --batch {brand}/ads/statics/{batch}
   ```

   It gives account status, dark stretches with no spend, hours each live ad set actually spent, 7 day spend, frequency, CTR, CPC, and every rejected or stuck ad. If the account is not ACTIVE, lead with that: billing beats every creative verdict.

2. **Results.** Get spend, purchases (or the KPI event) and cost per result per ad set from the human's export or store data. If the campaign optimises a proxy (link clicks), judge on store data, not Meta's results column.

3. **Decide per ad set** with `media-buying.md`:
   - Under about 24 live hours: too early, except an obvious clickbait kill.
   - Below 5 times KPI in spend: hold, and say how much more spend it needs.
   - Kill, hold, promote or scale, each with the rule it rests on.
   - Rejected ads: name them and the policy reason; fix the copy or image through the normal pipeline, never by hand editing in Ads Manager.

4. **Answer in this shape:**
   1. Headline: delivering or not, and the one thing that matters most.
   2. Table per ad set: live hours, spend, cost per result vs KPI, share of spend, CTR, frequency, verdict.
   3. Actions now, each saying whether it writes to Meta.
   4. What to leave alone and when to look again.

5. **Writes need a yes.** Pausing, enabling, budget changes and new launches change live spend. Ask first.

6. **When the batch hits its decision rule,** run `process-learnings.md`: call each tracker row winner or loser, update the angle files, and write the learning.

## Checks

- Every number quoted says where it came from (health.py check time, export date).
- Any verdict on an ad set with under 24 live hours says so.
- No Meta write happened without an explicit yes in this conversation.
- No token or credential appears in any output, file or commit.
