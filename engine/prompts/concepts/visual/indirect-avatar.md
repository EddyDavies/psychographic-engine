# Format: Indirect Avatar

> Targets the buyer through someone else's problem. Educational bridge to product as solution. Ingredient visuals build trust.
> Adapted from: 08-indirect-avatar (ingredient grid → educational hero composition)

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product photo (cutout preferred) | `products/images/spray-bottle/cutout.jpg` |
| `headline` | Question targeting avatar indirectly (under 40 chars) | "TODDLER INTO EVERY CUPBOARD?" |
| `subtext` | Educational bridge (under 120 chars) | "Many household sprays rely on harsh chemicals. Plant-based cleaners can still cut through grease and grime." |
| `ingredient_1` | Key ingredient/benefit | "Coconut-derived cleanser: cuts grease" |
| `ingredient_2` | Key ingredient/benefit | "Citric acid: lifts limescale" |
| `ingredient_3` | Key ingredient/benefit | "Lemon peel oil: fresh, not harsh" |
| `promo_text` | Optional promotional badge | "Free delivery today" |

## Prompt

### [FORMAT]

9:16 vertical portrait. Dark-to-warm gradient background.

### [BACKGROUND]

Gradient from dark (#1A1A1A) at the top to warm amber/gold at the bottom. Rich, warm, editorial. The gradient creates depth and draws the eye downward toward the product.

### [PRODUCTS]

Product from reference image, centred in the lower-middle area, well-lit against the gradient. Surrounded by real botanical elements that represent the ingredients — halved lemons, coconut pieces, fresh mint and fern fronds arranged around the product. The botanicals aren't in neat circles — they're scattered naturally around the product, creating a "what's inside" visual proof.

### [COPY_OVERLAY]

Top area — large bold headline in high-contrast colour (bright green or white):
"{headline}"
The question format creates engagement and targets the avatar indirectly.

Below headline — smaller white explanatory text:
"{subtext}"
This is the educational bridge from problem to solution.

Near the botanical elements — small white labels:
"{ingredient_1}"
"{ingredient_2}"
"{ingredient_3}"

Optional badge in corner:
"{promo_text}"

### [ACCENT_ELEMENTS]

Real botanical ingredients scattered around the product:
- Halved lemons and lemon peel
- Coconut pieces
- Fresh mint leaves
- Fern fronds
These must feel like real food photography — vibrant, appetizing, natural. NOT clip-art, NOT icons.

### [STYLE]

Educational and trustworthy. The question headline hooks the avatar indirectly — you're targeting the BUYER through a problem they want to solve for their home/family. The botanical ingredients build trust by showing what's inside. The gradient background feels premium and editorial. Think "wellness brand meets science" — not clinical, not hippie. Warm, knowledgeable, reassuring.

### [LEARNINGS]

- ADAPTATION NOTE: Original uses 9 circular ingredient images in a precise radial grid. NanoBanana can't produce precise radial layouts. Adapted to naturally scattered botanicals around the product, which NanoBanana handles well.
- Botanical elements render very well in NanoBanana — this is a strength of the tool for plant-based products
- The question headline must target the buyer INDIRECTLY — "Toddler into every cupboard?" targets the parent through the child's behaviour
- Ingredient labels near botanicals render ~50% of the time — the visual botanicals alone still communicate "natural ingredients"
- Dark-to-warm gradient renders reliably and creates a premium, editorial feel
- The educational subtext is critical — without it, the jump from "curious toddler" to "buy our cleaner" feels too abrupt
