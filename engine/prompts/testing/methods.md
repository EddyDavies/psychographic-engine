# Testing Methods Reference

## The Testing Cycle

Creative testing follows a two-phase cycle: **Discovery** and **Deep Iteration**. A/B Splits are a tactical tool used within either phase.

```
Discovery Batch → find winning angle
        ↓
Deep Iteration → maximise winning angle
        ↓
   (plateau) → back to Discovery Batch
```

The cycle repeats as angles fatigue. Each pass through Discovery should test fresh sub-avatars and angles from `ranked-angles.md`, informed by learnings from the previous cycle.

---

## Discovery Batch

Test multiple angles from different sub-avatars simultaneously to find which direction gets traction.

- **Goal:** Identify which angle/sub-avatar combination earns spend and engagement
- **Structure:** 3-5 angles from different sub-avatars, each with 1-2 hooks, same format and offer
- **Budget:** Spread evenly across angles — enough per angle to judge (minimum spend threshold)
- **Risk:** Higher per-angle (most will lose), lower strategically (you'll find a direction)
- **Source material:** Pull angles from `avatars/core-{name}/ranked-angles.md`, prioritising untested angles

**When to use:**
- New account with no performance data
- Current winning angle has plateaued
- Entering a new product or offer
- Existing angles exhausted

## Deep Iteration

Once a direction is found, test different executions, hooks, and styles of that specific angle to maximise its performance.

- **Goal:** Find the best execution of a proven angle
- **Structure:** Same angle, vary one element per variant (hook, visual style, format, CTA, awareness framing)
- **Budget:** Lower per-test (you're refining, not exploring)
- **Risk:** Low (building on proven performance)
- **Source material:** Winning angle's hook variations and the sub-avatar profile that drives it

**When to use:**
- Discovery Batch produced a clear winner
- A winner still has room to improve (hasn't plateaued)
- You want to test a new format or hook style on a proven angle

## A/B Split

Isolate a single variable, run both versions simultaneously. This is a tactical tool used within either Discovery or Deep Iteration when you need a definitive answer.

- **Goal:** Answer "does X or Y perform better?" with confidence
- **Structure:** Two variants, one variable changed, same budget and audience
- **Budget:** Higher (need sufficient volume per variant for statistical significance)
- **Risk:** Medium (one variant will underperform by design)

**When to use:**
- Within Discovery: "Does this angle work better as static or video?"
- Within Deep Iteration: "Does hook A or hook B drive more purchases?"
- Any time you need to isolate a specific variable rather than broadly explore

---

## Decision Tree

1. **New account or no performance data?** → Discovery Batch
2. **Have a winning angle that's still performing?** → Deep Iteration
3. **Winning angle plateauing or fatiguing?** → Discovery Batch (new cycle)
4. **Need to isolate a specific variable?** → A/B Split (within either phase)

---

## Processing Results

When analysing test results, go beyond structural observations. Identify:

- **Which sub-avatar** responded (map back to `avatars/core-{name}/`)
- **Which angle and desire** drove the result (reference `ranked-angles.md`)
- **Why it worked** in psychographic terms — not just "video outperformed static" but "the transformation narrative resonated with the identity-driven sub-avatar"

Update angle status in `ranked-angles.md` (`untested` → `testing` → `winner` / `loser`) and capture psychographic insights in `testing/learnings.md`.

The full checklist, including the strategy or execution diagnostic you run before retiring an angle, is `process-learnings.md`.

---

## A Note on Bulk Content Seeding

High-volume UGC or content seeding (sometimes called "Shotgun") is a content strategy concern, not a creative testing method. It doesn't belong in the test-and-learn cycle because it optimises for volume rather than isolating what works and why. If you're producing content at scale, that workflow lives outside this framework.
