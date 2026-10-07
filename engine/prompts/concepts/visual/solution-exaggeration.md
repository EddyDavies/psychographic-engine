# Format: Solution Exaggeration

> Bold number claim over a moody product-in-use photo. Dark overlay with white text and benefit bars.
> Adapted from: 02-solution-exaggeration

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product in-use or lifestyle photo (dark/moody preferred) | `products/images/spray-bottle/styled-01.jpg` |
| `headline_line_1` | Number + timeframe (under 25 chars) | "60 PODS." |
| `headline_line_2` | Outcome eliminated (under 25 chars) | "ZERO NEW BOTTLES." |
| `benefit_1` | First benefit bar text | "Cleans every room" |
| `benefit_2` | Second benefit bar text | "Plant-based formula" |
| `benefit_3` | Third benefit bar text | "No harsh chemical smell" |
| `benefit_4` | Fourth benefit bar text | "Streak-free on glass" |
| `accent_color` | Accent colour for benefit dots | "#D4A853" |

## Prompt

### [FORMAT]

9:16 vertical portrait. Full-bleed lifestyle photograph with dark overlay for text legibility.

### [BACKGROUND]

A close-up lifestyle scene showing the product in a real environment — dimly lit kitchen counter, evening atmosphere, warm under-cabinet lighting. The image should be dark enough (or have a dark overlay at 50-60% opacity) for white text to be highly legible across the entire frame. Natural, moody, editorial feel.

### [PRODUCTS]

Product from reference image is the environmental hero — it's IN the scene being used/displayed, not floating over it. The product should be visible but the scene matters more than a clean product shot.

### [COPY_OVERLAY]

Bold white condensed sans-serif text, top area:
"{headline_line_1}"
"{headline_line_2}"
Large, imposing, high contrast against the dark overlay.

Below the headline, four benefit lines with a thin horizontal bar and an accent-coloured ({accent_color}) dot on the right end of each:
"{benefit_1}"
"{benefit_2}"
"{benefit_3}"
"{benefit_4}"
White text, clean sans-serif, smaller than headline.

### [STYLE]

A direct-response ad that leads with a bold, specific claim. The moody photography makes the product feel serious and effective. The benefit bars create scannable proof points. Dark, confident, not cluttered. Think supplement brand meets premium household cleaning.

### [LEARNINGS]

- The number in headline_line_1 must be SPECIFIC — "60 pods" beats "lots of refills", "zero new bottles" beats "less waste"
- Benefit bars with accent dots render ~60% of the time — include the instruction, but the benefits text alone still works without the dots
- The background photo must be genuinely dark or the overlay instruction gets ignored — describe the scene as "dimly lit" or "evening"
- Full-bleed photo instruction is critical — without it NanoBanana creates a white-bordered layout
- Keep each benefit under 6 words for scannability
