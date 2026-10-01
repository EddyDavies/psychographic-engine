# Format: Avatar Callout

> Direct identity callout with testimonial card and product arrangement. Stops scroll by naming the avatar.
> Adapted from: 01-avatar-callout

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product arrangement photo (styled preferred) | `products/images/starter-kit/` |
| `headline` | Avatar identity callout, all caps (under 30 chars) | "MUMS WITH CURIOUS TODDLERS" |
| `headline_emoji` | Single emoji reinforcing the avatar | "🧒" |
| `reviewer_name` | Real customer name | "Sarah T." |
| `review_text` | Testimonial quote (under 200 chars) | "My mirrors are finally streak-free and the bathroom doesn't smell like bleach anymore" |

## Prompt

### [FORMAT]

9:16 vertical portrait OR 1:1 square. Smartphone-quality photo feel — not over-polished.

### [SCENE]

Clean, bright composition. White or very light background. The layout reads top-to-bottom: emoji + headline → testimonial card → product arrangement.

### [COPY_OVERLAY]

Top section — large, bold serif or impact headline in black, 2-3 lines with emoji:
{headline_emoji}
"{headline}"

Middle section — testimonial card with light gray (#F5F5F5) rounded-corner background:
Small circular avatar photo on the left (authentic, real person feel).
"{reviewer_name}" in bold.
"{review_text}" in dark gray (#333333), natural reading size.

### [PRODUCTS]

Bottom section — product arrangement from reference image. Multiple product variants on a neutral surface, soft studio lighting. Products are the clear anchor of the image. Tightly grouped, not spread out.

### [STYLE]

A direct-response Facebook ad that stops scroll by calling out a specific group of people. Feels personal and trustworthy — the testimonial card adds social proof. Clean, white, high-contrast. Not editorial, not luxury — honest and direct. For women 35-55 scrolling Facebook.

### [LEARNINGS]

- The headline MUST name the avatar directly — this is the scroll-stop mechanism. Generic headlines kill this format.
- Keep headlines under 5 words. "MUMS WITH CURIOUS TODDLERS" works. "WOMEN WHO WORRY ABOUT WHAT'S IN THEIR CLEANING PRODUCTS AND WANT SOMETHING PLANT-BASED" doesn't.
- Testimonial text must feel real — specific details ("my mirrors", "doesn't smell like bleach") beat generic praise ("great product")
- The circular avatar photo renders unreliably — sometimes NanoBanana ignores it. Include the instruction but don't rely on it.
- Emoji in the headline renders reliably and adds visual interest
- Product arrangement should use a styled reference image, not a cutout — this format needs warmth
