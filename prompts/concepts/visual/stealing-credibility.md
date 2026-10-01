# Format: Stealing Credibility

> Borrows authority from a known brand/concept. Close-up texture image with product and bold headline. Collage-style zones.
> Adapted from: 03-stealing-credibility (quad grid → collage composition)

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product photo (cutout or hand-held) | `products/images/spray-bottle/cutout.jpg` |
| `headline` | Authority-borrowing headline (under 40 chars) | "The Streak-Free Trick Window Cleaners Swear By" |
| `stat_1_number` | First proof stat number | "4,000+" |
| `stat_1_label` | First proof stat label | "Five-Star Reviews" |
| `stat_2_number` | Second proof stat | "1" |
| `stat_2_label` | Second proof stat label | "Pod Per Bottle" |
| `stat_3_number` | Third proof stat | "60" |
| `stat_3_label` | Third proof stat label | "Pods a Year" |
| `stat_4_number` | Fourth proof stat | "100%" |
| `stat_4_label` | Fourth proof stat label | "Plant-Based" |
| `accent_color` | Background accent colour | "#D4A853" |

## Prompt

### [FORMAT]

1:1 square preferred. Collage-style composition with distinct visual zones — not a clean single photo.

### [SCENE]

The image is composed in loose zones (not a rigid grid):
- One zone features the bold headline on a solid accent-coloured ({accent_color}) background
- One zone features an extreme close-up texture/macro shot — ingredients, botanicals, or product detail — filling the frame with satisfying visual detail
- One zone features the product, ideally held in a real hand (product from reference image)
- Stat numbers ({stat_1_number}: {stat_1_label}, etc.) appear as bold overlaid text elements across the composition

The zones feel like a curated collage or mood board — not a rigid 2x2 grid. Overlap, varied sizing, and slight asymmetry are good.

### [COPY_OVERLAY]

Headline on accent background zone:
"{headline}"
Bold, confident, dark text on coloured background.

Stats overlaid across the composition:
"{stat_1_number}" — {stat_1_label}
"{stat_2_number}" — {stat_2_label}
"{stat_3_number}" — {stat_3_label}
"{stat_4_number}" — {stat_4_label}
Numbers are large and bold; labels are smaller.

### [STYLE]

Curiosity-driven, authority-borrowing. The headline steals credibility from something the audience already trusts. The macro texture image creates visual interest and curiosity. The stats provide hard proof. This format works by association — your product gets borrowed credibility from the named reference. Bold, confident, slightly provocative.

### [LEARNINGS]

- ADAPTATION NOTE: Original is a rigid 2x2 grid — NanoBanana can't reliably produce precise grids. Described as "collage-style zones" which NanoBanana handles better (~60% usable outputs)
- The headline must reference a KNOWN brand or concept — obscure references kill the borrowed-credibility effect
- Macro/texture images of ingredients (lemon peel close-up, a pod dissolving in water, natural fibres) work well and NanoBanana generates them reliably
- Stats with specific numbers build credibility — round numbers feel made up
- "Hand holding product" renders ~50% of the time — include the instruction but have a fallback composition in mind
- 1:1 square works better than 9:16 for the collage feel
