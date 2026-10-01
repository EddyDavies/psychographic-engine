# Angle Brief Prompt

## When to Use

After selecting an angle from `angles.md` for ad creation. Produces a format-agnostic angle brief — the strategic core of an ad before any visual or messaging concept is applied. The brief feeds directly into the ad-assembly prompt.

## Inputs Required

- One angle entry from `clients/{client}/angles/angles.md`
- The target sub-avatar file(s) it references from `clients/{client}/avatars/`
- Product knowledge from `clients/{client}/products/`

## Prompt Template

```
You are a creative strategist building an angle brief — the strategic payload of an ad before any format decisions are made. This brief will later be combined with a visual concept and a messaging concept to produce a finished ad.

**Product Knowledge:**
[PASTE PRODUCT FILE CONTENTS]

**Angle:**
[PASTE THE SINGLE ANGLE ENTRY FROM angles.md]

**Target Sub-Avatar(s):**
[PASTE THE FULL SUB-AVATAR FILE(S) REFERENCED IN THE ANGLE'S Target Sub-Avatars]

### Instructions

1. Read the angle's Reason to Buy and Emotional Lever.
2. Read each target sub-avatar's Implied Beliefs, Emotions, Objections, and Awareness Level.
3. Build the brief below. Every field must be grounded in the inputs — do not invent claims or emotions not present in the sub-avatar or product data.

### Output Format

Output the brief in EXACTLY this format:

## Angle Brief

**Angle:** [Angle Name]
**Target Sub-Avatar:** [sub-avatar-name]

**Core Message:** [The Reason to Buy, restated as the single thing this ad must communicate]

**Emotional Lever:** [The implied belief or emotion from the sub-avatar that makes them ready to act — cite the specific belief/emotion from their profile]

**Key Proof Points:**
- [Claim or feature from product knowledge that supports the Reason to Buy]
- [Second proof point]
- [Third proof point, if applicable]

**Awareness Level:** [From the sub-avatar's profile — Problem Aware / Solution Aware / Product Aware / etc.]

**Objections to Pre-empt:**
- "[Objection from the sub-avatar]" — [how the ad should address it]
- "[Second objection]" — [how to address]

### Rules

- This brief is deliberately format-agnostic. No visual direction, no copy length, no image specs.
- The emotional lever must come from the sub-avatar's Implied Beliefs or Hooks That Resonate sections, not invented.
- Proof points must come from the product file, not assumed.
- If the angle targets multiple sub-avatars, pick the primary one and note the others as secondary audiences.
```

## Output Destination

Used as input to the ad-assembly prompt. Not saved as a standalone file.
