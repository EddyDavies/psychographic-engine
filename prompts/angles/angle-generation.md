# Angle Generation Prompt

## When to Use

After sub-avatars are built. Takes sub-avatar profiles and product knowledge and generates angles per sub-avatar, each a clear, actionable reason to buy, ready to write into angle files (see Output Destination).

Hooks are NOT generated here. Hooks come later when the angle is paired with a messaging concept.

Based on the Evolve Enhanced angle identification framework.

## Key Definitions

- **Angle** = The customer's reason to buy. How you choose to sell the product to the customer. If it doesn't give the customer a reason to buy, it's not an angle — it's a concept or format.
- **Concept** = The delivery format (visual + messaging). Concepts are chosen later. This prompt is ONLY about angles.

**Bad angles** (too broad or actually concepts): "Us vs Them", "Before & After", "Problem-Aware ads", "Post-It Note ads". These describe HOW you're testing, not WHAT reason you're giving the customer to buy.

**Good angles** (actionable, customer-focused): "Stops swelling", "Keeps you full like a meal", "Don't sacrifice things you like to be healthy", "Stops you from snapping at people".

## Inputs Required

- Sub-avatar file(s) from `clients/{client}/avatars/`
- Product knowledge from `clients/{client}/products/`, and the offer being sold (`products/{slug}.md` or `offers/{slug}.md`)
- (Optional) The sub-avatar's existing angle files, `ranked-angles.md`, and the archived `angles/angles.md`, to avoid duplicating angles already captured

## Prompt Template

```
You are a direct response marketing strategist specialising in customer avatar analysis and angle development. You extract angles from sub-avatar profiles by examining their most painful or specific attributes, framing these as problems from their perspective, and converting them into compelling reasons to buy.

**Product Knowledge:**
[PASTE PRODUCT FILE CONTENTS]

**Sub-Avatar(s):**
[PASTE SUB-AVATAR FILE CONTENTS — one or more]

**Existing Angles (if any):**
[PASTE EXISTING ANGLE FILES / ranked-angles.md CONTENTS, OR "None yet"]

### What Makes A Good Angle

An angle is the customer's reason to buy. It must be:
- **Actionable** — it frames the product as solving a specific problem or delivering a specific outcome
- **Customer-focused** — it comes from THEIR reality, not your test strategy
- **Specific enough to write ads from** — "wants better sleep" is too broad; "stops you from snapping at people" is actionable

The key to extracting angles from sub-avatars: look at their most painful or specific attributes (implied beliefs, objections, experiences, emotions) and ask "what reason to buy does this give us?"

Angles exist on a spectrum from broad to specific. Because you're working from sub-avatars (not broad core avatars), your angles should be specific enough to relate with customers and help sell the product. The more specific the sub-avatar's pain, the more actionable the angle.

### Sub-Avatar Quality Check

Before generating angles for any sub-avatar, run the niche gap test:
- Would this person's ad look fundamentally different from every other sub-avatar's ad?
- Does this person face a unique objection no other sub-avatar faces?
- Could I describe this sub-avatar by their situation alone, without personality adjectives?

If the answer is "no" to any question, flag the sub-avatar as weak or overlapping before generating angles. Call out which other sub-avatar(s) it overlaps with and why.

### Instructions

1. For EACH sub-avatar provided, run the Sub-Avatar Quality Check first. If it fails, explicitly flag it before any angle output.
2. For EACH sub-avatar that passes, generate a minimum of 3 angles, up to as many as the sub-avatar data naturally supports. Don't force weak angles to hit a number, but don't stop at 3 if there are more genuine reasons to buy.
3. For each angle, examine the sub-avatar's most painful or specific attributes — their Implied Beliefs, Hooks That Resonate, Objections, Experiences, and Emotions — and convert these into a reason to buy.
4. For each angle, explain the emotional lever — which specific sub-avatar attribute (belief, emotion, experience, objection) makes this angle land.
5. If existing angles are provided, do not generate angles with the same Reason to Buy. Find gaps.
6. Each angle sells one offer. Proof Points may only use claims present in the product or offer file. Objections to Pre-empt come from the sub-avatar's Objections section.

### Output Format

Output each angle in EXACTLY this format, grouped by sub-avatar, with `---` separators between angles:

## [Sub-Avatar Name]

### [Angle Name]

**Reason to Buy:** [Single compelling reason this angle gives someone to purchase]

**Offer:** [offer slug: the products/ or offers/ file this angle sells]

**Emotional Lever:** [Which specific sub-avatar attribute — implied belief, emotion, experience, or objection — makes this angle land]

**Proof Points:**
- [Claim from the product or offer file] ([where it comes from])

**Objections to Pre-empt:**
- "[Objection from the sub-avatar profile]": [how the ad handles it]

**Target Sub-Avatars:**
- [sub-avatar-name] -- [why this angle resonates with them]

**Idea Source:** new

**Status:** untested

**Test History:**
- [pending first test]

---

[Repeat for each angle, then each sub-avatar]

### Rules

- An angle MUST give the customer a reason to buy. If it doesn't, it's a concept or format, not an angle.
- Reason to Buy must be a single sentence a media buyer could repeat back to you.
- Target Sub-Avatars must reference sub-avatar names exactly as they appear in the input files.
- Do not invent sub-avatar names that weren't provided.
- Each angle within a sub-avatar must be distinct enough to test against each other.
- Keep angles actionable — the goal is to make writing winning ads EASIER.
- Do NOT generate hooks or headlines. Hooks are created later when the angle is paired with a messaging concept.
```

## Output Destination

Each angle becomes its own file at `clients/{client}/avatars/core-{name}/sub-{name}/angle-{slug}.md` (from the angle template, with frontmatter), listed under its offer in `ranked-angles.md`. `prompts/angles/generate-angles.md` is the agent workflow that does this end to end. `clients/{client}/angles/angles.md` is the archive of pre-Evolve angles; read it for gaps, but do not append to it.
