# Ad Assembly Prompt

Two-step process: LLM writes reviewable ad copy, then image gen renders the visual with on-image text it composes itself.

## Step 1: Copy Generation (LLM)

Writes the primary text and headline only. On-image text (headlines, callouts, whiteboard text) is NOT written here — the image model handles that so it fits the layout naturally.

### Inputs Required

- Angle brief (output of the angle-brief prompt)
- One messaging concept file from `prompts/concepts/messaging/`
- Brand voice, visual identity, and no-gos from `clients/{client}/brand/`

### Prompt Template

```
You are a direct response copywriter. Write ad platform copy (primary text + headline) for a Meta ad.

**Angle Brief:**
[PASTE ANGLE BRIEF OUTPUT]

**Messaging Concept:**
[PASTE THE FULL MESSAGING CONCEPT FILE CONTENTS]

**Brand Voice, Visual Identity & No-Gos:**
[PASTE BRAND VOICE / VISUAL IDENTITY / NO-GOS FILE CONTENTS]

### Instructions

1. Read the messaging concept's Structure and Examples.
2. Write primary text that follows the messaging concept's pattern while delivering the angle brief's Core Message.
3. The opening line must use the messaging concept's structure applied to the angle's reason to buy.
4. Address at least one objection from the angle brief's Objections to Pre-empt list.
5. End with a CTA.
6. Respect all brand no-gos.
7. Carry the client's visual identity into the image prompt so the image model sees the correct colour, font, and layout constraints.

### Output Format

## Primary Text

[3–6 sentences. This is the text field above the image in the ad platform. Must follow the messaging concept's structure.]

## Headline

[Max 40 characters. Reinforces the Core Message. This is the ad platform's headline field, NOT text on the image.]

### Rules

- Follow the messaging concept's structure — don't just write generic copy.
- Do not add claims not present in the angle brief's Proof Points.
- Do not use language flagged in the brand no-gos.
- Do NOT write on-image text (headlines, callouts, whiteboard copy). That happens in Step 2.
```

### Output Destination

Hold for human review before Step 2.

---

## Step 2: Image Generation (NanaBanana 2)

After copy is approved, the image model gets the visual concept template + angle brief + messaging concept direction. It composes on-image text itself so it fits the layout aesthetically.

### Inputs Required

- Approved primary text + headline from Step 1
- Angle brief
- One visual concept file from `prompts/concepts/visual/`
- One messaging concept file from `prompts/concepts/messaging/`
- Product reference image
- Brand voice, visual identity, and no-gos from `clients/{client}/brand/`

### Image Prompt Structure

The image generation prompt is built by combining:

1. The visual concept's Prompt Template (layout, camera, environment, vibe)
2. A messaging direction block that tells the image model what to communicate

Replace visual concept placeholders with direction, not locked-in copy:

```
[MESSAGING DIRECTION — for the image model to compose on-image text]
Angle: [angle name]
Core Message: [from angle brief]
Messaging Concept: [concept name + structure pattern, e.g. "[Pain point]? Not anymore."]
Proof Points: [from angle brief]
The on-image text should communicate the core message using the messaging concept's pattern. Compose text that fits the layout naturally.
```

The image model writes on-image text (headlines, callouts, whiteboard copy) to fit the visual format. It has creative latitude on exact wording, length, and positioning.

### Output Destination

Save images to `clients/{client}/ads/statics/`
