# Annotated Lifestyle Flexible

Flexible version of the annotated lifestyle format with design principles instead of rigid visual specs. Products on the right, text on the left, with visual indicators connecting benefit callouts to products. Gives the model more creative latitude while keeping the direct-response structure.

## When to Use

When you want the annotated lifestyle layout but need more visual variety across iterations. The flexible design principles (rather than exact specs like "gold dots") produce more diverse outputs. Good for generating multiple variants in a batch without them all looking identical.

## Inputs

| Placeholder | Description | Example |
|---|---|---|
| Reference image | Product photo to reproduce in the scene | fernwood-starter-kit.png |
| `[SECONDARY HEADLINE]` | Small line above main headline, under 8 words | FOR THE CUPBOARD UNDER YOUR SINK |
| `[HEADLINE LINE 1]` | Main headline first line, 2–4 words | REAL CLEAN. |
| `[HEADLINE LINE 2]` | Main headline second line, 2–4 words | ZERO HARSH SMELL. |
| `[CALLOUT 1]` | First benefit callout | Plant-Based Formula |
| `[CALLOUT 2]` | Second benefit callout | One Pod = One 500ml Bottle |
| `[CALLOUT 3]` | Third benefit callout | Streak-Free on Glass |
| `[CALLOUT 4]` | Fourth benefit callout | No New Plastic Bottles |
| `[BADGE CONTENT]` | Optional badge/price element | £24 (was £32) |

## Prompt Template

```
[CAMERA]
Smartphone or mid-range DSLR quality — not studio-polished. Shot from a low angle, roughly table height, angled slightly upward toward the products. Portrait/vertical aspect ratio — approximately 9:16 or 4:7. Slight natural depth of field — products in sharp focus, background softly blurred. No dramatic lighting, no AI glow, no lens flare.

[SUBJECT]
The hero product arrangement occupies the right half of the frame. Use the products shown in the reference image — match their appearance, packaging, labels, and colours exactly. Do NOT name, identify, or invent any products — defer entirely to the reference image. Arrange them in a tightly grouped cluster at slightly varying heights, closely grouped, almost touching — dense, curated, kit-like. Products are the sharpest element in the image. Camera angle is low enough that products feel large and dominant, filling roughly 60–70% of the vertical height.

[SURFACE]
Products sit on a real surface appropriate to the environment — visible and grounding. Products are placed ON the surface, not floating.

[BACKGROUND]
A real domestic interior — not a studio, not a gradient, not a plain wall. The background must be noticeably darker and more muted than the products — it should recede, not compete. Soft-focus interior elements barely legible — atmospheric rather than detailed. Muted warm tones. The left side of the image must be especially dark to ensure text is highly legible. The background may include soft warm bokeh, warm window light, or other atmospheric light elements if they add depth without competing with the products.

[DESIGN PRINCIPLES]
This is a direct-response conversion ad, not a brand awareness piece. Every design choice should serve clarity and persuasion.

Use colour, weight, and scale to establish clear visual hierarchy between the headline, sub-elements, and callouts. The headline must dominate. Accent colours should feel warm and premium — golds, ambers, warm whites. Choose colours that communicate luxury without being flashy.

Use visual indicators to connect benefit callouts to the products — ticks, dots, lines, icons, or other graphic elements. Choose whichever approach feels most natural for the composition. These indicators should feel precise and intentional, like a product diagram or infographic, not decorative.

Typography should mix weights and potentially styles to create visual interest — the secondary headline can use a contrasting style (script, italic, lighter weight) if it adds warmth and personality without sacrificing legibility.

[COPY — THIS IS CRITICAL, ALL TEXT MUST APPEAR IN THE IMAGE]
The left half of the image carries all text, overlaid directly on the image. No text boxes, no banners, no panels.

Secondary headline (small, above the main headline, flush left):
'[SECONDARY HEADLINE]'

Main headline (dominant, flush left, two lines):
'[HEADLINE LINE 1]'
'[HEADLINE LINE 2]'

Four benefit callouts (below the headline, vertically stacked with generous spacing):
'[CALLOUT 1]'
'[CALLOUT 2]'
'[CALLOUT 3]'
'[CALLOUT 4]'

Social proof element (below or near the callouts):
★★★★★ 4,000+ Five-Star Reviews

No text on the right half. No invented copy beyond what is specified.

[BADGE — OPTIONAL]
If it strengthens the ad, include a badge or price callout element in the bottom-left area:
[BADGE CONTENT]
The badge should feel like a natural part of the ad, not a sticker slapped on top. Use colours and style consistent with the rest of the design.

[VIBE]
A premium direct-response Facebook ad — warm, inviting, built for conversion. The aesthetic is closer to a curated home edit than a luxury editorial. Products are the hero but the feeling is value, quality, and treat-yourself indulgence. Warm and authentic, like it was photographed in someone's real home. For women 40-55 scrolling Facebook. Not cold, not clinical, not studio-lit. Not a mood board, not a spa ad.
```

## Learnings

- Do NOT include any brand name or product type in the prompt — naming products triggers model priors that override the reference image. Defer entirely to the reference image for product identity.
- Avoid product-related words in background/context prompts (e.g. "gift", "Christmas") — they can trigger model priors that change product appearance.
- Background must be a specific real environment — a plain gradient or neutral wall always reads as wrong.
- Background must be explicitly described as darker and more muted than the products.
- Portrait/vertical aspect ratio (9:16 or 4:7) must be specified explicitly or output defaults to square.
- Products must be described as tightly clustered — without this AI spreads them across the surface.
- Camera angle must be low to make products feel large and imposing.
- Headlines must be 2–4 words per line. Secondary headlines under 8 words.
- Design principles (hierarchy, indicators, typography contrast) produce better and more diverse results than prescribing specific visual treatments (gold dots, checkmarks, etc.).
- Social proof (stars + review count) should always be included — no reason not to.
- Price badge is optional but renders reliably and adds conversion value.
- Negative instructions ("do NOT use a gradient") are necessary to prevent the model defaulting to clean commercial aesthetics.
