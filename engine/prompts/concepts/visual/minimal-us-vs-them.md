# Format: Minimal Us vs Them

> Reversed comparison — lists competitor's problems, your product says "None of that." Clean split on bold background.
> Adapted from: 13-minimal-us-vs-them (graphic badges → overlaid callout text)

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Your product photo (cutout preferred) | `products/images/spray-bottle/cutout.jpg` |
| `competitor_description` | What the "them" product looks like | "A generic plastic supermarket spray bottle" |
| `them_label` | Header for competitor side | "Them" |
| `brand_label` | Header for your side | "Fernwood" |
| `competitor_callout_1` | Negative callout for competitor | "Harsh chemical smell" |
| `competitor_callout_2` | Negative callout | "Leaves streaks" |
| `competitor_callout_3` | Negative callout | "New plastic bottle every time" |
| `competitor_callout_4` | Negative callout | "Warning labels" |
| `dismissal_text` | Your side's response | "None of that." |
| `bg_color` | Bold background colour | "#2C3E50" |

## Prompt

### [FORMAT]

1:1 square preferred. Bold solid-colour background ({bg_color}).

### [SCENE]

Split composition on bold coloured background:
- LEFT SIDE ("Them"): A generic/mass-market version of the product category ({competitor_description}). Surrounded by white callout text labels scattered around it at angles — each one a negative attribute:
  "{competitor_callout_1}"
  "{competitor_callout_2}"
  "{competitor_callout_3}"
  "{competitor_callout_4}"
  The callouts create visual clutter around the competitor product — clutter IS the message.

- RIGHT SIDE ("Brand"): Your product from reference image, clean and uncluttered. Just the product and:
  "{dismissal_text}"
  Simple, confident, clean.

Thin white vertical divider between the two sides. Headers "{them_label}" and "{brand_label}" above each side.

### [STYLE]

The message is in the contrast: their side is cluttered with problems, your side is clean and simple. "None of that." is the mic drop — it's confident enough to not even list benefits. The bold background colour makes this pop in the feed. Slightly provocative, very confident. Think brand that knows exactly what it isn't.

### [LEARNINGS]

- ADAPTATION NOTE: Original uses rounded badge elements around the competitor product. NanoBanana can't reliably produce precise badge graphics. Adapted to scattered white text labels, which render more reliably (~60%).
- The competitor must be RECOGNISABLE but not specifically named — "generic plastic supermarket spray" works, naming a brand could cause legal issues
- 4 negative callouts is the sweet spot — fewer feels weak, more clutters both sides
- The dismissal text must be SHORT — "None of that." is perfect. Don't list your own benefits; the confidence of the dismissal IS the benefit.
- Bold solid-colour backgrounds render very reliably — this is a NanoBanana strength
- The vertical divider renders ~60% of the time — the composition still works without it
- Your product side MUST be visually cleaner than the competitor side — that's the whole point
- You may need to provide a reference image for the competitor product too — NanoBanana may hallucinate something too different from the category
