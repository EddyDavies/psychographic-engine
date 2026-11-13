# Ranked Angles: core-careful-parent

> Fictional worked example. Fernwood is not a real brand.

> PRIORITY NOTE: You do NOT have to test each angle separately.
> Test the #1 hook from the STRONGEST sub-avatar first.
> Layer supporting angles from other sub-avatars into body copy.

Angles are grouped by offer (the product or bundle the ad sells), because an angle is one sub-avatar's reason to buy one offer. Within each offer, sub-avatars are ranked by strength: confidence in the profile plus how directly the offer answers their situation. Each sub-avatar gets 3 angles per offer (Evolve framework).

> Format rules (read by `engine/scripts/generate-ads.py`): keep sub-avatar headings as `## sub-{name}`, angle lines as `**Angle N: Name**`, the `Reason to Buy:` line, and the `-> [full angle](...)` link exactly as shown. Offer headings use `# Offer:` so they never collide with sub-avatar headings.

Both sub-avatars are low confidence (one research source each). Every angle below is untested, and every one must pass `../../brand/no-gos/no-gos.md`: no safety, non-toxic or germ claims, and no children shown with the product.

---

# Offer: starter-kit

## sub-toddler-opening-cupboards (strongest for this offer; confidence: low)

**Angle 1: One Tin on the High Shelf**
Reason to Buy: The Starter Kit swaps a cupboard of mixed bottles for four bottles and one lidded tin that lives on a high shelf, so childproofing the kitchen is one thing to put away instead of eleven.
Hook: **"Four bottles. One tin. One high shelf."**
-> [full angle](sub-toddler-opening-cupboards/angle-one-tin-on-the-high-shelf.md)

**Angle 2: Know Every Ingredient**
Reason to Buy: Every pod's full ingredient list is short and printed on the tin, and they fill the bottles themselves, so they know exactly what is in every bottle in the house.
Hook: **"Know every word on the label."**
-> [full angle](sub-toddler-opening-cupboards/angle-know-every-ingredient.md)

**Angle 3: The Bleach Can Leave the House**
Reason to Buy: The kit's bathroom pod shifts limescale with citric acid, so the bottle of bleach they worry about most no longer has to live under the sink.
Hook: **"Shiny taps. No bleach."**
-> [full angle](sub-toddler-opening-cupboards/angle-bleach-can-leave-the-house.md)

---

## sub-weaning-high-chair (second strongest for this offer; confidence: low)

**Angle 1: Unscented for the Tray**
Reason to Buy: The Starter Kit comes with Unscented all-purpose pods and a short ingredient list on the tin, so the high chair tray gets properly cleaned with nothing perfumed left where the baby eats.
Hook: **"Nothing on the tray you can't read."**
-> [full angle](sub-weaning-high-chair/angle-unscented-for-the-tray.md)

**Angle 2: Cuts What Baby Wipes Smear**
Reason to Buy: The all-purpose spray lifts the greasy film that baby wipes just push around the tray, so they stop going through a pack of wipes a day and still not getting it clean.
Hook: **"Baby wipes don't clean the tray."**
-> [full angle](sub-weaning-high-chair/angle-cuts-what-wipes-smear.md)

**Angle 3: A Bottle That Lives by the High Chair**
Reason to Buy: The kit's four bottles mean one Unscented bottle can live permanently by the high chair, so it is in reach mid-mess instead of in the cupboard across the room.
Hook: **"The bottle that lives by the high chair."**
-> [full angle](sub-weaning-high-chair/angle-a-bottle-by-the-high-chair.md)

---

# Offer: refill-subscription

## sub-weaning-high-chair (strongest for this offer; confidence: low)

Only this sub-avatar has angles on the subscription: weaning is the situation that uses the most spray. `sub-toddler-opening-cupboards` has no subscription angles yet.

**Angle 1: Never Run Out Mid-Mealtime**
Reason to Buy: Weaning gets through all-purpose spray faster than anything else in the house, and the refill subscription posts 15 pods through the letterbox every three months, so the bottle is never empty when dinner is on the floor.
Hook: **"Empty spray. Dinner on the floor."**
-> [full angle](sub-weaning-high-chair/angle-never-run-out-mid-mealtime.md)

**Angle 2: Wipe All You Like at 80p a Bottle**
Reason to Buy: On the refill subscription a full bottle costs 80p, so they can spray the tray, table and floor after every meal without rationing it or reaching for the wipes to save money.
Hook: **"80p a bottle. Wipe all you like."**
-> [full angle](sub-weaning-high-chair/angle-wipe-all-you-like.md)

**Angle 3: Change the Mix as She Grows**
Reason to Buy: The refill subscription lets them set the pod mix (all Unscented all-purpose during weaning, more bathroom pods later) and skip a delivery when the tin is full, so the plan fits this stage of the baby and the next one.
Hook: **"Weaning now. Bath time next."**
-> [full angle](sub-weaning-high-chair/angle-change-the-mix-as-she-grows.md)

---

# Testing Priority

For each offer: start with the strongest sub-avatar, Angle 1. Test that hook first in a Discovery batch.
If it earns spend, run Deep Iteration on it. If not, move to the next sub-avatar's Angle 1.

Current state (2026-09-15): nothing tested yet for this core avatar.
1. `starter-kit`: a Discovery batch of `one-tin-on-the-high-shelf`, `unscented-for-the-tray` and `know-every-ingredient` (three angles, two sub-avatars, one format).
2. `refill-subscription`: hold until there are Starter Kit buyers from this core avatar to retarget (Most Aware), then test `never-run-out-mid-mealtime`.
3. Before either, gather a second research source for both sub-avatars to raise confidence.
