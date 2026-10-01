# Format: Annotated Lifestyle

> Product bundle on a real surface with benefit callouts connected by gold lines. Left-half text, right-half products.

## Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `reference_images` | Product/bundle photos | `products/images/starter-kit/` |
| `secondary_headline` | Small caps line above main headline | "THE FERNWOOD STARTER KIT" |
| `headline_line_1` | Main headline first line (2-4 words) | "YOUR CUPBOARD" |
| `headline_line_2` | Main headline second line (2-4 words) | "DESERVES THIS" |
| `callout_1` | First benefit callout | "Plant-Based Formula" |
| `callout_2` | Second benefit callout | "Streak-Free on Glass" |
| `callout_3` | Third benefit callout | "One Pod = One 500ml Bottle" |
| `callout_4` | Fourth benefit callout | "4 Bottles, One Starter Kit" |

## Prompt

[CAMERA]
Smartphone or mid-range DSLR quality — not studio-polished. Shot from a low angle, roughly table height, angled slightly upward toward the products. Portrait/vertical aspect ratio — approximately 9:16 or 4:7. Slight natural depth of field — products in sharp focus, background softly blurred. No dramatic lighting, no AI glow, no lens flare.

[SUBJECT]
The hero product arrangement occupies the right half of the frame. Use the products shown in the reference image — match their appearance, packaging, labels, and colours exactly. Do NOT name, identify, or invent any products — defer entirely to the reference image. Arrange them in a tightly grouped cluster at slightly varying heights, closely grouped, almost touching — dense, curated, kit-like. Products are the sharpest element in the image. Camera angle is low enough that products feel large and dominant, filling roughly 60–70% of the vertical height.

IMPORTANT — LEFT-TO-RIGHT ARRANGEMENT: The tall upright packaging boxes MUST be on the LEFT side of the product cluster, closest to the text. The remaining products sit in the CENTRE and RIGHT.

[SURFACE]
Products sit on a warm wooden kitchen worktop with natural grain — visible and grounding.

[BACKGROUND]
A real domestic kitchen interior. The background must be noticeably darker and more muted than the products. Soft-focus interior elements barely legible — atmospheric rather than detailed. The left side of the image must be especially dark to ensure white text is highly legible. Muted warm tones — soft ambers, warm greys. Do NOT use a gradient, plain wall, or studio setup.

[COPY_OVERLAY — THIS IS CRITICAL, THE IMAGE MUST INCLUDE ALL OF THIS TEXT]
The left half of the image carries all text overlaid directly on the image. This text is a critical part of the ad — it MUST appear.

Secondary headline above the main headline, flush left:
'{secondary_headline}' — bold white sans-serif, all caps, noticeably smaller than the main headline (one-third to one-half the size).

Main headline directly below, two lines:
'{headline_line_1}' — heavy white sans-serif, all caps, very large, bold
'{headline_line_2}' — same font, same size, same weight
Both lines flush left, tight leading.

Below the headline, four benefit callouts listed vertically with generous spacing:
'{callout_1}'
'{callout_2}'
'{callout_3}'
'{callout_4}'

Each callout in bold white sans-serif, sentence case — thick and highly legible, roughly half the headline size. Each callout has a thin straight horizontal gold line (#D4A853) extending rightward toward the products, ending in a small filled gold circle dot. Four dots at four distinct vertical points on different products. Lines are straight horizontal rules only.

No drop shadows. No text on the right half. No invented copy beyond what is specified.

[STYLE]
A direct-response Facebook ad for a premium product bundle — warm, inviting, built for conversion. Curated home edit feel, not luxury editorial. Products are the hero, feeling is value and treat-yourself indulgence. Warm, authentic, like it was shot in someone's home. For women 40-55 on Facebook. Do NOT produce anything cold, clinical, or studio-lit.

### [LEARNINGS]
- Do NOT include any brand name or product type in the prompt — naming products triggers model priors that override the reference image. Defer entirely to the reference image for product identity
- Avoid product-related words in background/context prompts (e.g. "gift", "Christmas") — they can trigger model priors that change product appearance
- Background must be a specific real environment — a plain gradient or neutral wall always reads as wrong
- Background must be explicitly described as darker and more muted than the products
- Portrait/vertical aspect ratio (9:16 or 4:7) must be specified explicitly or output defaults to square
- Products must be described as tightly clustered — without this AI spreads them across the surface
- Camera angle must be low to make products feel large and imposing
- Headlines must be 2-4 words per line. Secondary headlines under 8 words
- Gold connector lines/dots render ~50% of the time — include the instruction but don't rely on it
- Negative instructions ("do NOT use a gradient") are necessary to prevent the model defaulting to clean commercial aesthetics
