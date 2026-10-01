# Format: Simplified Us vs Them

> Simple "This is X. This is Y." transformation comparison with two images and captions.
> Adapted from: 11-simplified-us-vs-them (graphic split → split-scene photo)

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product photo for the "after" side | `products/images/spray-bottle/styled-01.jpg` |
| `caption_left` | "Before" / generic caption (under 25 chars) | "This is a spray bottle." |
| `caption_right` | "After" / your product caption (under 25 chars) | "This is the last one." |
| `tagline` | Bridge statement (under 60 chars) | "One pod replaces one plastic bottle." |

## Prompt

### [FORMAT]

1:1 square preferred. Clean, white, minimal.

### [SCENE]

Two images side by side, equal size, filling the top 60% of the frame:
- LEFT: A universally recognised "generic" version of the category — plain, boring, mass-produced. Think stock supermarket plastic cleaning spray. Shot on white background, plain, deliberately unexciting.
- RIGHT: Your product from reference image — beautiful, premium, aspirational. Same photographic style as left (white background, same angle) but the product itself tells the story.

The visual contrast does the work — no need to label which is "better."

### [COPY_OVERLAY]

Below each image — clean sans-serif captions:
Left: "{caption_left}"
Right: "{caption_right}"

Below both — smaller gray tagline, centred:
"{tagline}"

### [STYLE]

Clean, honest, instantly understood. The format is so simple it feels transparent — no hard sell, just a visual truth. The comparison is implicit, not aggressive. Two objects, two labels. The viewer draws their own conclusion. White background, clean typography, zero clutter. Think "brand that doesn't need to try hard."

### [LEARNINGS]

- ADAPTATION NOTE: Original is a precise graphic split layout. NanoBanana can produce side-by-side photos when explicitly described, but the split isn't always clean (~50% usable). Describing it as "two images side by side" works better than "split screen."
- The "before" image should be a UNIVERSALLY KNOWN object — if people don't instantly recognise it, the comparison fails
- Both images must be shot in the SAME style — same background, same angle. Mismatched styles break the comparison.
- Captions must follow the "This is X. This is Y." pattern exactly — deviating kills the format's clarity
- The tagline adds credibility through specificity — year founded, location, heritage details work well
- 1:1 square works best — 9:16 creates too much empty space
- NanoBanana sometimes struggles to generate a "generic/boring" product — you may need to provide a reference image for the left side too
