# Ranked Angles: core-low-waste-household

> Fictional worked example. Fernwood is not a real brand.

> PRIORITY NOTE: You do NOT have to test each angle separately.
> Test the #1 hook from the STRONGEST sub-avatar first.
> Layer supporting angles from other sub-avatars into body copy.

Angles are grouped by offer (the product or bundle the ad sells), because an angle is one sub-avatar's reason to buy one offer. Within each offer, sub-avatars are ranked by strength: confidence in the profile plus how directly the offer answers their situation. Each sub-avatar gets 3 angles per offer (Evolve framework).

> Format rules (read by `engine/scripts/generate-ads.py`): keep sub-avatar headings as `## sub-{name}`, angle lines as `**Angle N: Name**`, the `Reason to Buy:` line, and the `-> [full angle](...)` link exactly as shown. Offer headings use `# Offer:` so they never collide with sub-avatar headings.

This core avatar has angles on one offer only. The refill subscription is sold to it later, once a sub-avatar has bought the kit (see `../../offers/refill-subscription.md`).

---

# Offer: starter-kit

## sub-let-down-eco-switcher (strongest for this offer; confidence: high)

**Angle 1: Proves It Actually Cleans**
Reason to Buy: The Starter Kit cleans glass streak-free from one pod and tap water, so going green no longer means a worse clean.
Hook: **"Your eco spray smeared the mirror. This won't."**
-> [full angle](sub-let-down-eco-switcher/angle-proves-it-actually-cleans.md)

**Angle 2: Your Last Eco Spray Was Mostly Water**
Reason to Buy: Her last eco spray failed because it was a weak, ready-mixed liquid, and the Starter Kit's pods put a full dose in every bottle, so this switch is different for a reason she can understand.
Hook: **"Most of your spray bottle is water."**
-> [full angle](sub-let-down-eco-switcher/angle-most-of-your-spray-is-water.md)

**Angle 3: Second Switch, No Risk**
Reason to Buy: If the Starter Kit doesn't clean as well as the spray she went back to, she gets her money back and keeps the bottles, so trying green a second time costs her nothing.
Hook: **"As clean as your old spray, or free."**
-> [full angle](sub-let-down-eco-switcher/angle-second-switch-risk-free.md)

---

## sub-flat-share-no-storage (second strongest for this offer; confidence: medium)

**Angle 1: Get the Cleaning Shelf Back**
Reason to Buy: Four bottles and one pocket-sized tin of pods replace the shared shelf of half-used plastic sprays, so the flat gets its shelf back.
Hook: **"One shelf. Four flatmates. Eleven bottles."**
-> [full angle](sub-flat-share-no-storage/angle-cupboard-space-back.md)

**Angle 2: Even Your Flatmates Can Refill It**
Reason to Buy: Refilling is drop a pod in and add tap water, so whoever empties the bottle can refill it on the spot and the job stops falling on them.
Hook: **"Even your flatmates can refill this."**
-> [full angle](sub-flat-share-no-storage/angle-refill-in-ten-seconds.md)

**Angle 3: The Kit Moves With You**
Reason to Buy: The four bottles and the tin are theirs to keep and pack in one box when the tenancy ends, so it is the last cleaning stuff they buy for a flat, not money left behind for the next tenants.
Hook: **"The last spray bottles you'll leave behind."**
-> [full angle](sub-flat-share-no-storage/angle-moves-with-you.md)

---

## sub-subscription-sceptic (third strongest for this offer; confidence: medium)

Angles regenerated on 2026-09-01 after `refill-not-reorder` was retired on a strategy loss (see `../../testing/learnings.md`). The retired file stays in the folder with `status: loser` and is deliberately not listed here.

**Angle 1: Buy It Once, Nothing Renews**
Reason to Buy: The Starter Kit is a one-off purchase with no plan attached, so they can switch to refills without signing up to anything.
Hook: **"Buy it once. Nothing renews."**
-> [full angle](sub-subscription-sceptic/angle-buy-once-nothing-renews.md)

**Angle 2: Pods Don't Go Off**
Reason to Buy: Dry pods keep for two years in the tin, so buying the kit can never turn into a drawer of refills going to waste.
Hook: **"Pods don't go off."**
-> [full angle](sub-subscription-sceptic/angle-pods-dont-go-off.md)

**Angle 3: The Price, With No Catch**
Reason to Buy: The Starter Kit is £24 and every price after it is printed up front (93p a bottle one-off), so there is no hidden plan behind the low entry price.
Hook: **"£24. That's the whole catch."**
-> [full angle](sub-subscription-sceptic/angle-price-with-no-catch.md)

---

# Testing Priority

For each offer: start with the strongest sub-avatar, Angle 1. Test that hook first in a Discovery batch.
If it earns spend, run Deep Iteration on it. If not, move to the next sub-avatar's Angle 1.

Current state (2026-09-15):
1. `proves-it-actually-cleans` won the `c01` Discovery batch and is in Deep Iteration (`c03`). Keep it there until it plateaus.
2. `cupboard-space-back` lost `c01` as a static on execution; next is a UGC video format test as its own concept.
3. When `c03` plateaus, run a Discovery batch of the untested Angle 1s: `buy-once-nothing-renews` with Angle 2 of each of the other two sub-avatars.
