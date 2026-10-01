# Format: Pubity Style

> Native-feeling social post with full-bleed product hero, small story circle photo, and text overlay bar.
> Adapted from: 12-pubity-style

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Dramatic product-in-action photo | `products/images/spray-bottle/styled-01.jpg` |
| `headline` | Hook text with trailing "..." (under 120 chars) | "WHY IS THE CUPBOARD UNDER YOUR SINK FULL OF HALF-USED BOTTLES? THIS SMALL BRITISH BRAND HAS THE ANSWER..." |
| `story_image_description` | Who/what appears in the small circle | "Close-up of a woman dropping a concentrate pod into a glass spray bottle, relaxed smile" |

## Prompt

### [FORMAT]

9:16 vertical portrait OR 1:1 square. Full-bleed photography — no borders, no margins.

### [BACKGROUND]

Full-bleed lifestyle/product-in-action photograph from reference image. Dramatic, editorial quality. Close crop showing product + environment. Dark enough at the bottom for white text overlay. Shallow depth of field, high contrast, slightly moody.

### [COPY_OVERLAY]

Top-right corner — small circular photo (like an Instagram story bubble) with white border:
{story_image_description}
This creates narrative and curiosity.

Bottom area — dark gradient overlay (transparent at top → 70% black at bottom):
White bold condensed headline text:
"{headline}"
The "..." trailing off creates click-through imperative.

Thin white horizontal divider above the text. Small white brand wordmark centred on the divider.

### [STYLE]

Looks like an organic social media post, not an ad. The story circle, full-bleed photo, and bottom text bar mimic native platform content. The headline creates curiosity without revealing everything. This format BLENDS into the feed — the scroll-stop comes from the content, not the format screaming "AD". Editorial, native, curiosity-driven.

### [LEARNINGS]

- The story circle photo renders ~40% of the time — include the instruction but don't rely on it
- The "..." at the end of the headline is CRITICAL — it creates the curiosity gap and click-through urge
- Headlines work best as questions ("WHY...?") or incomplete revelations ("THIS SMALL BRAND HAS...")
- The bottom gradient overlay renders reliably — NanoBanana handles this well
- Full-bleed instruction must be explicit — without it NanoBanana adds white borders
- The hero image must be genuinely dramatic/editorial — boring product shots kill this format
- Styled reference images work much better than cutouts — this format needs atmosphere
