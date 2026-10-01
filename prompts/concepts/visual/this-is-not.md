# Format: This Is Not

> Product redefinition through contradiction. Creates curiosity gap by reframing what the product appears to be.
> Adapted from: 04-this-is-not (split layout → dramatic single composition)

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product in "result state" (styled preferred) | `products/images/spray-bottle/styled-01.jpg` |
| `headline_line_1` | Contradictory statement part 1 | "This isn't a spray bottle." |
| `headline_line_2` | Reframe part 2 | "It's the last one you'll buy." |
| `stat_1` | Proof stat | "1 pod = 1 bottle" |
| `stat_2` | Proof stat | "Plant-based formula" |
| `stat_3` | Proof stat | "4,000+ five-star reviews" |
| `price_text` | Price callout (optional) | "From £24" |
| `accent_color` | Background/accent colour | "#D4A853" |

## Prompt

### [FORMAT]

9:16 vertical portrait OR 1:1 square.

### [BACKGROUND]

Solid accent colour ({accent_color}) or warm dark background. Bold and confident — the colour makes this ad stand out in the feed.

### [PRODUCTS]

Large product image from reference — the product in its "result state" (spray bottle in use on a kitchen counter, not in packaging). Prominent, taking up 40-50% of the frame. The product should look like what the headline claims it IS, not what it isn't.

### [COPY_OVERLAY]

Bold headline, large, high-contrast against background:
"{headline_line_1}"
"{headline_line_2}"
The contradiction creates a curiosity gap — the viewer needs to reconcile the two statements.

Stat pills or small text elements near the product:
"{stat_1}" · "{stat_2}" · "{stat_3}"
Small, proof-like, supporting the reframe.

Price callout (if provided) in a clean circle or badge:
"{price_text}"

### [STYLE]

Clever, provocative, curiosity-driven. The contradiction in the headline stops the scroll — "wait, what IS it then?" The stats prove the reframe is legitimate. The bold background colour makes this pop in the feed. Confident and slightly cheeky, not aggressive. Think brand that knows it's underestimated and enjoys the reveal.

### [LEARNINGS]

- ADAPTATION NOTE: Original has a precise left/right split layout. NanoBanana can't reliably produce split compositions. Adapted to a single dramatic product-on-colour composition.
- The contradiction MUST create genuine cognitive dissonance — "This isn't a spray bottle. It's the last one you'll buy." works. "This isn't just a cleaner. It's a great cleaner." doesn't.
- Stat pills render ~50% reliably. As fallback, stats can appear as simple text lines.
- Price circle/badge renders ~40% of the time — keep price text simple
- Bold solid-colour backgrounds work very well in NanoBanana — more reliable than gradients
- The product must visually support the REFRAME, not the "isn't" — show it as a permanent fixture on the counter, not looking like a disposable plastic bottle
