# Format: Studio Product Hero

> Monochromatic studio hero shot. Two-tone surface/wall, tight product cluster, elegant text overlay.

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product/bundle photos | `products/images/starter-kit/` |
| `headline` | Elegant script/serif headline (2-5 words) | "clean, refill, repeat" |
| `subline` | All-caps sans-serif subline (under 8 words) | "THE PLANT-BASED CLEANING STARTER KIT" |

## Prompt

[FORMAT]
9:16 vertical portrait format. Camera is at product eye-level or just slightly above — roughly 5-10 degrees of elevation, looking almost straight at the products. This is a hero shot, not a flatlay. The products should feel imposing, close, and monumental — filling the lower two thirds of the frame. The full image is filled with scene — no white borders, no studio void, no empty dead zones at top or bottom.

[BACKGROUND]
Muted, dusty, slightly desaturated sage green: a deep, soft, earthy green tone that feels like a painted wall with depth and texture rather than a bright digital colour. Not lime, not mint, not teal, not vivid emerald. Lean toward the darker, dustier, more muted end of the sage-olive spectrum; think a desaturated sage deepened toward fern, not a saturated or vivid green. The background is a solid painted wall or seamless backdrop. Colour is completely consistent and even across the full frame — no gradient, no vignette, no shift to darker or lighter tones at the edges, no darkening at the corners. The background reads as a single confident, muted colour block. Do NOT allow any vignetting, corner darkening, or edge darkening in the background.

[SURFACE]
A flat tabletop surface in a lighter pale sage tone, clearly distinct from the darker wall behind it. The surface and wall are two separate tones: the table is a soft, muted pale sage and the wall behind is the deeper fern green. There is a visible horizon line where the table meets the wall — this is intentional and gives the scene depth and grounding. The surface is smooth and matte — no visible grain, no linen texture. Products sit ON the table, not floating in a colour void.

[PRODUCTS]
Show all the unique items from the reference image. Arrange them in a tight, compact, closely grouped cluster — products are almost touching, with near-zero visible surface gap between them. The arrangement feels like a starter kit that has just been unpacked and set out together. Not perfectly symmetrical, not rigidly grid-aligned, but densely grouped rather than spread across the surface. Do NOT spread products across the surface with visible gaps between them. Products overlap slightly and vary in height — taller items toward the back, shorter items in the foreground. The overall cluster should feel dense and kit-like — not sparse, not spread out. Do NOT create a symmetrical or staged-looking arrangement — it should feel casually curated and asymmetric. Products are the clear subject of the image — nothing competes with them.

[ACCENT_ELEMENTS]
No food, no botanicals, no fruit or flowers. The only accent elements are product packaging boxes — propped open or leaning casually behind the product cluster. No props, no fabric, no ribbon, no scattered petals.

[LIGHTING]
Warm, soft, diffused studio lighting — the scene is evenly lit with no harsh shadows. The primary light source is soft and directional, coming from slightly above and to one side, creating gentle shadow depth beneath the products without drama. Soft highlights catch the edges of the glass bottles, with gentle, natural refraction through the glass. No dramatic spotlighting, no AI glow, no lens flare, no reflections on the surface. The overall mood is warm and intimate, not clinical or high-contrast.

[COPY_OVERLAY]
Text appears in the upper third of the image, centred horizontally, overlaid directly on the background — no text box, no banner, no pill shape, no drop shadow box. Two lines of text:
Line 1: "{headline}" — set in a flowing, elegant script or lowercase serif font, white, large, relaxed and confident.
Line 2: "{subline}" — set in a clean, tight all-caps sans-serif font, white, significantly smaller than line 1, with wide letter-spacing. Sits directly below line 1 with a small gap. No other text in the image. No price callouts, no badges, no starburst graphics.

[STYLE]
A premium lifestyle product kit shot — the kind of image you'd see in a curated brand email or a high-end retailer's seasonal campaign. It feels considered and tasteful, not cluttered. The monochromatic sage palette makes the whole image feel cohesive and intentional — like the products were designed to exist in this exact colour world. Warm and inviting, not cold or corporate. The light catching the glass makes it feel tactile rather than sterile. This is aspirational but accessible — not a luxury fashion house, not a discount brand. Think: a well-loved British eco cleaning brand doing a seasonal starter kit edit. The image should feel like something worth saving to a Pinterest board. Not a 3D render. Not over-retouched. No AI glow. No symmetry for symmetry's sake. No empty dead zones anywhere in the frame.

### [LEARNINGS]
- Do NOT describe specific products in the prompt — always defer to the reference image for product identity. Describe arrangement and composition, not individual items.
- Do NOT include any brand name in the prompt — AI models will hallucinate brand names onto product labels.
- Product cluster must be described as tightly grouped and compact with near-zero visible surface gap between items — without this instruction, AI spreads products across the surface.
- Background tone should be anchored toward the darker, dustier, more muted sage end — without this, AI defaults to a lighter, more saturated or vivid green.
- Background must include explicit instruction against vignetting and corner darkening — without this, AI frequently darkens the upper corners.
- The surface and background wall must be TWO distinct tones — without this, AI blends them into a single colour void that removes all depth.
- Headlines must be 2-5 words max. Sublines must be under 8 words.