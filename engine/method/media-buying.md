# Media Buying

How to judge live ads and move spend. Based on the Evolve framework (How To Run Ads, How To Manage Ads, How To Analyze Ads). Applied by `engine/prompts/testing/launch-and-assess.md`; delivery facts come from `engine/scripts/meta/health.py`.

Examples use Fernwood (refill cleaning pods) selling the Fernwood Starter Kit, with a target cost per purchase (KPI) of £20.

## Structure

- One campaign per batch, budget on the campaign (CBO), highest volume bidding. No cost caps or bid caps while testing.
- Every ad set in the campaign has identical settings and targeting. The only thing that differs between ad sets is the creative concept.
- One concept is one ad set, shaped 3:2:2: three visuals of the concept, each with its own primary text and headline. Build what the batch has and report the gap; never invent missing pieces.
- A champions ad set holds proven ads and is the bar. A new concept is a winner only if it takes spend from champions at or under KPI.
- No ad set minimum or maximum spend. Kill whole ad sets on spend and KPI instead.
- `engine/scripts/meta/launch.py` builds exactly this.

## When Meta optimises a proxy

Evolve reads Meta's spend as a vote: an ad that gets no spend is a bad ad. That holds only when Meta optimises for the purchase. If the campaign optimises link clicks or landing page views (no pixel yet, a blocked dataset, too few purchases to exit learning), spend follows cheap clicks, not buyers. Then **cost per purchase from your own store data outranks share of spend.** High share plus a cheap CPC plus a poor purchase rate is the clickbait pattern, not a winner.

## Judge timing

- Day 1 is noise. Judge on at least 3 days of averages; run to 7 only if there is traction by day 3; never past 14.
- Count **hours live, not calendar days.** A billing hold, a rejection or a paused day is not a test day. Run `health.py` before trusting "day 2".
- Under about 24 live hours, nothing but an obvious clickbait kill is judgeable.
- Scaling needs 48 to 72 hours of consistent results.

## Kill

- Kill at ad set level, not ad level. Inside a concept, never switch off the variant Meta favoured to force spend onto the others.
- Starved and missing KPI after 7 days: kill. Kill these first to make room for new tests.
- Taking spend at a bad KPI: can go within 24 to 48 hours, but Meta often pulls spend back itself, so usually wait a day or two.
- Misclick guard: landing page views per click well below the healthy ads, or a cheap CPC with a poor purchase rate, means kill.
- Minimum spend before any KPI kill: 5 times KPI. Fernwood: £100 on a concept before calling it on cost per Starter Kit.

## Hold

- Never switch off something that was working and dipped; zoom out to the averages.
- Champions are never switched off. A set at KPI on its own stays on even when it trails champions.
- Never switch off working campaigns to restructure. Move only what is broken.

## Promote

- A winner takes the majority of spend at KPI and the campaign as a whole improves. Under 10% of 7 day spend is a loser; 30 to 50% is probably a winner. When Meta optimises a proxy, require the KPI as well, never share alone.
- Promote by duplicating the ad into champions, which keeps its engagement (post IDs are the fallback). Keep the original set running unless the champions copy outspends it.
- A creative that cannot beat champions at KPI is not a new winner.

## Scale

- Up 20% a day after 48 to 72 hours above KPI; 1.5x to 2x when 33 to 50% under the KPI.
- Down 20% after 48 to 72 hours below target, never below a floor. The fix for a falling account is outside the ad account: new concepts, funnel bugs, offers, the landing page.
- Each ad set should be able to take 3 times KPI a day. Fernwood: £60 per ad set, so a £200 daily budget carries about 3 concept sets beside champions.
- Under a few hundred a day, keep to about 5 ad sets including champions.

## Fatigue

- Frequency 1.5 or under is prospecting. Frequency 3 with a tiny share of spend is Meta saying the ad is bad; review anything above 3.
- Winners older than 3 months are suspect; 6 months at most.
- Champions below KPI for 7 days, or a CTR drop on champions: queue a creative refresh, do not restructure.
- Roller coaster results come from moods, the market and Meta itself. The controllable fix is strategy (permanent desires, a lower awareness entry, a matching landing page), never restructuring.

## Diagnose a loser

- Link CTR soft target over 1%, good over 1.5%. Soft metrics sit behind spend and results.
- Clicks without purchases: the landing page or the offer, not the ad. Compare purchase rate per click across concepts on the same page before blaming creative.
- Rewrite before retiring: an iteration of a loser can become an account's top spender. Use the strategy or execution diagnostic in `execution.md`.

## Weekly loop

- Weekly review, about 1.5 hours: every winner, one loser per batch, the rest marked winner or loser in the tracker; plan 3 to 4 new concepts and 1 to 2 landing pages. Learnings go through `engine/prompts/testing/process-learnings.md`.
- Do not start a new test week late in the week; let current tests run through the weekend and judge on Monday.
- Discovery first, then deep iteration on what hit (see `angles-and-testing.md`). The hit rate for statics is about 5%.

## Not used at small spend

Cost cap ("zombie") campaigns, ABO scaling (under about $1k a day), and 3:2:2:2 landing page tests (over about $2k a day; use a landing page test ad set instead).

## Conflicts between lessons

Kill timing ranges from 24 to 48 hours to at least 7 days. Resolve it as: judge a fed ad set from day 3, a starved one at day 7, always on live hours and never under 5 times KPI.
