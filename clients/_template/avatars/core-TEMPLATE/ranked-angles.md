# Ranked Angles: core-{name}

> PRIORITY NOTE: You do NOT have to test each angle separately.
> Test the #1 hook from the STRONGEST sub-avatar first.
> Layer supporting angles from other sub-avatars into body copy.

Angles are grouped by offer (the product or bundle the ad sells), because an angle is one sub-avatar's reason to buy one offer. Within each offer, sub-avatars are ranked by strength: confidence in the profile plus how directly the offer answers their situation. Each sub-avatar gets 3 angles per offer (Evolve framework).

> Format rules (read by `scripts/generate-ads.py`): keep sub-avatar headings as `## sub-{name}`, angle lines as `**Angle N: Name**`, the `Reason to Buy:` line, and the `-> [full angle](...)` link exactly as shown. Offer headings use `# Offer:` so they never collide with sub-avatar headings.

---

# Offer: {offer-slug}

## sub-{name} (strongest for this offer; confidence: [low/medium/high])

**Angle 1: [Actionable Name]**
Reason to Buy: [one sentence]
Hook: **"[best hook]"**
-> [full angle](sub-{name}/angle-{slug}.md)

**Angle 2: [Actionable Name]**
Reason to Buy: [one sentence]
Hook: **"[best hook]"**
-> [full angle](sub-{name}/angle-{slug}.md)

**Angle 3: [Actionable Name]**
Reason to Buy: [one sentence]
Hook: **"[best hook]"**
-> [full angle](sub-{name}/angle-{slug}.md)

---

## sub-{name} (second strongest for this offer)

...

---

# Offer: {second-offer-slug}

## sub-{name} (strongest for this offer)

...

---

# Testing Priority

For each offer: start with the strongest sub-avatar, Angle 1. Test that hook first in a Discovery batch.
If it earns spend, run Deep Iteration on it. If not, move to the next sub-avatar's Angle 1.
