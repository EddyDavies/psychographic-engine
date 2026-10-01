# Ad Creation Pipeline

Every ad starts with a sub-avatar. This is the mandatory sequence — never skip steps or reorder.

## Pipeline

```
Step 1          Step 2               Step 3            Step 4              Step 5
Sub-Avatar  →   Angle Generation →   Angle Brief   →   Pick Concepts   →   Ad Assembly
(one person)    (her reasons to      (format-agnostic  (messaging +        (hook is born here
                 buy, from HER        strategy doc)     visual)             from angle × concept)
                 pain/beliefs)
```

### Step 1 — Pick a Sub-Avatar

Choose one sub-avatar from `clients/{client}/avatars/sub-*.md`. Read her full profile: implied beliefs, objections, emotions, experiences, awareness level. She is the foundation — everything flows from her reality.

**Input:** Sub-avatar file
**Output:** Understanding of who you're talking to

### Step 2 — Generate Angles

Run `prompts/angles/angle-generation.md` with the sub-avatar profile + product knowledge. This produces angles — specific reasons to buy grounded in her pain, beliefs, and objections.

Do not reuse generic angles. Do not pick angles first and find a sub-avatar to match. The sub-avatar's profile drives which angles emerge.

**Input:** Sub-avatar file(s) + product knowledge
**Output:** 3+ angles per sub-avatar, appended to `clients/{client}/angles/angles.md`
**Prompt:** `prompts/angles/angle-generation.md`

### Step 3 — Generate Angle Briefs

For each angle you want to turn into an ad, run `prompts/angles/angle-brief.md`. This produces a format-agnostic creative brief — the strategic core before any visual or copy treatment.

**Input:** One angle + its target sub-avatar file(s) + product knowledge
**Output:** Angle brief (ephemeral — passed to Step 5, not saved)
**Prompt:** `prompts/angles/angle-brief.md`

### Step 4 — Pick Concepts

Choose one or more messaging concepts from `prompts/concepts/messaging/` and one or more visual concepts from `prompts/concepts/visual/`. Each angle brief will be combined with each concept pairing.

**Input:** Browse available concepts
**Output:** Selected concept files

### Step 5 — Assemble Ads

Run `prompts/concepts/ad-assembly.md` for each combination of angle brief × messaging concept × visual concept. The hook/headline is born here — from the collision of the angle's reason to buy with the messaging concept's structure. Hooks are never pre-written.

**Input:** Angle brief + one visual concept + one messaging concept + product reference image + brand voice
**Output:** Image prompt + primary text + headline, saved to `clients/{client}/ads/statics/`
**Prompt:** `prompts/concepts/ad-assembly.md`
**Post-step:** Append one row per variant to `clients/{client}/testing/creative-tracker.csv`

## Rules

- **Sub-avatar first, always.** No exceptions. The sub-avatar's reality is the foundation.
- **One avatar, one desire, one message per ad** (Rule of One).
- **Angles are reasons to buy**, not formats or concepts. If it doesn't give the customer a reason to buy, it's not an angle.
- **Hooks are not written until Step 5.** They emerge from the angle × messaging concept collision.
- **Angle briefs are ephemeral.** They exist to pass strategy into ad assembly, not as standalone files.
- **Check the tracker before assembling.** Filter `creative-tracker.csv` to confirm the sub-avatar x angle x messaging x visual combination hasn't been tried. After assembling, append new rows.
