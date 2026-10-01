# Flat-Lay Product Grid

Top-down editorial flat-lay with products arranged on a textured surface, surrounded by botanical accents. Headline and subline overlaid directly on the image. Works for bundle/offer ads where you want to show the full product spread.

## When to Use

Bundle or starter kit offers where the value story is "look how much you get." Best for Product Aware to Most Aware audiences who already know the brand and need an offer push. The editorial aesthetic positions it as premium but the direct copy drives conversion.

## Inputs

| Placeholder | Description | Example |
|---|---|---|
| Reference image | Photo of the full product collection | fernwood-starter-kit.png |
| `[HEADLINE TEXT]` | 2–5 word headline | CLEAN WITHOUT THE PLASTIC |
| `[SUBLINE TEXT]` | Under 8 words | The complete Fernwood Starter Kit |

## Prompt Template

```
[CAMERA]: A top-down flat-lay photograph shot on a DSLR with a 50mm lens. Soft, even lighting from a large diffused source above — no harsh shadows. Shallow depth of field is not visible because the plane is flat. Slight warmth in the white balance. The image feels editorial but not over-retouched — like a real product shoot, not a 3D render.
[SUBJECT]: All the Starter Kit products arranged in a loose, intentional grid on a muted warm beige surface (like kraft paper or linen). The kit box with its kraft paper sleeve sits at the centre as the anchor piece. The four glass spray bottles are spaced around it. The tin of concentrate pods and a few loose pods are placed nearby. Nothing is perfectly aligned — there's a slight "styled by hand" asymmetry.
[BOTANICAL ACCENTS]: Scattered organic elements are spread across the ENTIRE frame — not just around the products. A fern frond and a few mint leaves drift into the top corners and margins near the headline text. A halved lemon, a few lime wedges, a slice of pink grapefruit, a small mint leaf cluster, and a single sprig of eucalyptus fill the gaps between products in the centre. The botanicals create a continuous, cohesive flat-lay that wraps the whole image — there should be no empty "dead zone" at the top.
[COPY OVERLAY]: "[HEADLINE TEXT]" is set in a clean, modern serif font (large, top third of the frame). "[SUBLINE TEXT]" sits beneath it in a smaller, lighter weight. Both are overlaid directly on the image — no text box or banner. The text colour is dark charcoal (#2C2C2C) to contrast the pale background.
[BACKGROUND]: The surface is a warm beige or soft sand tone that fills the ENTIRE frame edge to edge — including behind the headline text at the top. The warmth is consistent throughout; there is no shift to white or grey at the top. The surface has clearly visible texture (linen weave, kraft paper grain, or natural fibre) that is apparent even in the areas where text is overlaid. It should feel like everything — text, products, botanicals — is sitting on one continuous tactile surface.
[VIBE]: A curated "unboxing spread" that feels premium but approachable — like something you'd see on a lifestyle Instagram account, not a luxury magazine. Clean but not sterile. Warm but not cosy. The composition should feel like a single continuous flat-lay from edge to edge. There should be no empty, stark, or tonally different area anywhere in the frame — especially not at the top where the text sits. The overall impression is: "this is a beautiful deal."
```

## Learnings

- Headlines must be 2–5 words max. Sublines must be under 8 words. Longer copy causes the model to add its own text or create cluttered layouts.
- Never describe text styling using words the model might render literally. Do NOT write "large and bold" or "crossed out in a lighter weight" near the text content — the model will render "LARGE & BOLD" as the actual ad text. Keep styling descriptions minimal and physically separate from the text strings.
- Strikethrough / crossed-out text is unreliable. For price anchoring, combine into a single string like "£24 (was £32)" rather than separate styled elements.
- 1:1 (square) ratio is more prone to splitting into a "text zone" and "product zone" with a visible horizontal boundary. For square variants, reinforce that botanicals and texture must extend into the top area even more aggressively.
- The best outputs have text that feels like it sits WITHIN the flat-lay scene, not floating above it. Botanicals near the text edges are what create this effect.
