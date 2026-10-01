# Format: Specific Pain Point

> Dramatic product hero with moody lighting, bold CTA text, price strikethrough, and guarantee. Leans into a visceral pain point.
> Adapted from: 05-specific-pain-point

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product photo (cutout or moody styled) | `products/images/starter-kit/` |
| `cta_headline` | Bold pain-point CTA (under 40 chars) | "BANISH STREAKY MIRRORS FOR GOOD" |
| `mechanism_label` | What makes it work | "Residue-Free Plant-Based Formula" |
| `price_current` | Current price | "£24" |
| `price_original` | Was price (optional) | "£32" |
| `guarantee_text` | Risk-reversal text | "30-DAY MONEY-BACK GUARANTEE" |
| `bg_color` | Background gradient base colour | "#2C1810" |
| `accent_color` | CTA and price highlight colour | "#D4A853" |

## Prompt

### [FORMAT]

9:16 vertical portrait. Dramatic product hero with dark moody background.

### [BACKGROUND]

Deep, rich gradient background matching {bg_color} — dark and atmospheric. Not black, but deeply coloured. Moody ambient light suggesting warmth without illuminating the background.

### [PRODUCTS]

Product arrangement from reference image, centred, imposing. Shot from a slightly low angle to make products feel large and dominant. Moody lighting matching brand colours — warm, dramatic, not clinical. Products fill the middle 50% of the frame.

### [COPY_OVERLAY]

Top area — small mechanism pill (white background, dark text):
"{mechanism_label}"

Price area (top-right) — was/now pricing:
"{price_original}" crossed through, "{price_current}" in bold, small "DEAL" badge in accent colour.

Bottom area — bold accent-coloured ({accent_color}) CTA text, large:
"{cta_headline}"

Below CTA — small, light gray, all-caps:
"{guarantee_text}"

### [STYLE]

A hard-hitting direct-response ad that names a specific, emotionally charged problem and offers the solution with urgency. The moody product hero shot makes the product feel premium and serious. The price strikethrough and guarantee remove friction. This is a conversion ad, not a brand ad. Dark, confident, urgent.

### [LEARNINGS]

- The CTA headline must use a VISUAL VERB — "banish", "eliminate", "transform" — not passive language
- Price strikethrough renders unreliably as separate elements. Combine into a single string like "£24 (was £32)" as fallback
- "DEAL" badge renders ~40% of the time — acceptable, the price contrast alone works
- Guarantee text should be small and understated — it's a trust signal, not a headline
- Dark backgrounds work best when described as a specific colour, not just "dark" — NanoBanana defaults to pure black otherwise
- Low camera angle instruction is critical for making products feel imposing
