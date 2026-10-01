# Format: Annotated Lifestyle Hero

> Bold headline hero with annotated fact pointers connecting to products in a lifestyle scene.

Lifestyle product hero with bold headline and annotated facts. Products are placed in a real environment (not a flat studio background) with text overlaid directly on the image. Facts use gold annotation pointer lines connecting to the products.

## Variables

| Variable | Description | Example (Fernwood) |
|---|---|---|
| `{product_reference_image}` | Photo of the full product collection/lineup | fernwood-starter-kit.png |
| `{background}` | One sentence describing the lifestyle environment | A warm oak kitchen worktop beside a window. Blurred tiled splashback and plants behind, soft morning light. |
| `{headline_line1}` | Smaller caps line at top | THE PRICE OF 12 BOTTLES. |
| `{headline_line2}` | VERY large hero line | 60 PODS. |
| `{headline_line3}` | VERY large hero line | A YEAR. |
| `{fact1}` | First annotated fact | Plant-Based Formula |
| `{fact2}` | Second annotated fact | Streak-Free on Glass |
| `{fact3}` | Third annotated fact | No Harsh Chemical Smell |
| `{fact4}` | Fourth annotated fact | 4 Bottles, One Starter Kit |

## Prompt

CRITICAL — PRODUCT ACCURACY: The reference image shows a unique, one-of-a-kind product collection that has never existed before. You MUST reproduce every single item EXACTLY as it appears in the reference image. Do not add, remove, or modify any products. Do not invent additional items. Match every detail — shape, colour, labels, materials, proportions — precisely from the reference. If it is not in the reference image, it should not be in the output.

Reference image: The complete product collection — reproduce this EXACT arrangement of items.

[LAYOUT]
9:16 vertical portrait. Lifestyle product hero with text overlaid directly on the image.

[BACKGROUND / ENVIRONMENT]
{background}
Natural depth of field — environment behind the products is slightly blurred. Soft, warm ambient lighting.

[PRODUCT_ARRANGEMENT]
Place the EXACT products from the reference image on the surface. Same items, same quantity, same arrangement style — kit box behind, products clustered naturally in front. Reproduce every item precisely. The collection should feel generous and premium.

[HEADLINE — TOP OF FRAME]
Bold, large white sans-serif text at the very top, overlaid on a subtly darkened area. Three lines:
Line 1 (smaller, caps): "{headline_line1}"
Line 2 (VERY large, heavy, caps): "{headline_line2}"
Line 3 (VERY large, heavy, caps): "{headline_line3}"
Takes up roughly the top 30-35% of the frame.

[ANNOTATED FACTS — LEFT SIDE]
Four facts listed vertically down the left side in bold white sans-serif text. Each fact has a thin gold/amber horizontal line extending rightward toward the products, with a small gold dot at the end. The lines act like annotation pointers connecting each claim to the product lineup. Subtle dark gradient on the left for text legibility.
1. "{fact1}"
2. "{fact2}"
3. "{fact3}"
4. "{fact4}"

[VIBE]
Premium, warm, lifestyle editorial. High-end eco cleaning brand shot for a magazine — but with the directness and clarity of a performance ad. The annotation lines give it a modern, architectural quality. Warm and inviting but confident and informative. NOT a flat studio shot — atmosphere, depth, warmth.

### [LEARNINGS]

- Do NOT include the competitor/inspiration ad as a reference image — the model will copy it wholesale. The layout is fully captured in the prompt text.
- Do NOT describe products in text (e.g. "4 spray bottles, 1 pod tin") — the model will hallucinate its own version. Instead use a product reference image and tell the model to reproduce it exactly.
- The "unique products that have never existed before" framing is critical — it stops the model from using priors to modify or substitute products.
- Use the full product collection photo as a single reference image rather than individual product shots — this gives the model the complete arrangement to reproduce.
- Flat solid-colour backgrounds don't work well for products that are visually lightweight (clear glass, white packaging). Lifestyle environments with depth of field give them context and presence.
- The gravitas comes from the lifestyle setting + bold overlaid text, not from making individual products appear larger.
