# Competitor Analysis Prompt

## When to Use

During onboarding or before new test cycles to understand the competitive landscape.

## Inputs Required

- 3-5 competitor names/URLs
- Their ad library links (Meta Ad Library)
- Landing page URLs

## Prompt Template

```
You are a competitive intelligence analyst specializing in direct response advertising. Analyse the following competitors and extract their marketing strategies.

**Competitors:**
1. [NAME] — Website: [URL] | Ad Library: [META AD LIBRARY LINK] | Landing Page: [URL]
2. [NAME] — Website: [URL] | Ad Library: [META AD LIBRARY LINK] | Landing Page: [URL]
3. [NAME] — Website: [URL] | Ad Library: [META AD LIBRARY LINK] | Landing Page: [URL]
4. [NAME] — Website: [URL] | Ad Library: [META AD LIBRARY LINK] | Landing Page: [URL]
5. [NAME] — Website: [URL] | Ad Library: [META AD LIBRARY LINK] | Landing Page: [URL]

### For Each Competitor, Extract:

1. **Brand Positioning** — Premium / Value / Niche / Mass Market
2. **Primary Desire Targeted** — What core desire does their marketing speak to?
3. **Marketing Frameworks Used** — Problem-Solution, Hero/Villain, Before/After, Us vs. Them, Story-based, etc.
4. **Hook Styles and Patterns** — Question hooks, bold claims, social proof leads, curiosity gaps, etc.
5. **Ad Formats** — Static / Video / UGC / Carousel / Mixed
6. **Tone and Language Register** — Formal / Casual / Scientific / Emotional / Aspirational
7. **Unique Mechanisms Claimed** — Proprietary processes, ingredients, methods, or frameworks they claim
8. **Offers and Pricing Strategy** — Discounts, bundles, free trials, guarantees, payment plans

### Output Format

**Comparison Table:**

| Dimension | Competitor 1 | Competitor 2 | Competitor 3 | Competitor 4 | Competitor 5 |
|-----------|-------------|-------------|-------------|-------------|-------------|
| Positioning |           |             |             |             |             |
| Primary Desire |        |             |             |             |             |
| Framework |             |             |             |             |             |
| Hook Style |            |             |             |             |             |
| Ad Format |             |             |             |             |             |
| Tone |                  |             |             |             |             |
| Unique Mechanism |      |             |             |             |             |
| Offer Strategy |        |             |             |             |             |

**Gaps & Opportunities:**
Identify what competitors are NOT doing. Look for:
- Desires none of them are targeting
- Frameworks none of them are using
- Audience segments they are ignoring
- Tones or styles absent from the landscape
- Objections none of them are addressing
```

## Output Destination

Save to `clients/{client}/research/competitor-analysis-{YYYY-MM-DD}.md`
