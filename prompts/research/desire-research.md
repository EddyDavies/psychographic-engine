# Desire Research Prompt

## When to Use

Before building avatars for a new client, or when expanding into a new product category.

## Inputs Required

- Product category
- Target market description
- Competitor URLs (3-5)
- Review sources (Amazon, Trustpilot, Reddit, forums)

## Prompt Template

```
You are a consumer psychology researcher specializing in desire mapping. I need you to analyse the following product category and market to identify the core desires driving purchase behavior.

**Product Category:** [INSERT PRODUCT CATEGORY]
**Target Market:** [INSERT TARGET MARKET DESCRIPTION]
**Competitor URLs:** [INSERT 3-5 COMPETITOR URLS]
**Review Sources:** [INSERT REVIEW SOURCES - Amazon, Trustpilot, Reddit, forums]

### Step 1: Identify Desires Across the 6 Mass Instincts

For each of the following instincts, identify all relevant desires:

1. **Health** — Survival, stay alive, stay healthy
2. **Sex** — Be attractive, find a mate
3. **Status** — Be important, respected
4. **Belonging** — Fit in, have friends
5. **Control** — Have power, predict outcomes
6. **Comfort** — Make life easier, avoid pain

### Step 2: Classify Each Desire

For each desire found, classify it as:
- **Surface** — Explicitly stated by customers in reviews, comments, or conversations
- **Hidden** — Implied or underlying; not directly stated but clearly driving behavior

### Step 3: Rate Each Desire on Desire Power

Score each desire on three dimensions (1-10 scale):
- **Scope** (1-10): How many people share this desire?
- **Urgency** (1-10): How pressing is this desire right now?
- **Staying Power** (1-10): Will this desire persist over time?

### Step 4: Output Format

Present findings as a table with the following columns:

| Desire | Mass Instinct | Surface/Hidden | Scope | Urgency | Staying Power | Evidence (quote or source) |
|--------|---------------|----------------|-------|---------|---------------|---------------------------|
|        |               |                |       |         |               |                           |

After the table, provide:
- Top 5 desires ranked by combined Desire Power score
- Any desires that appear across multiple Mass Instincts (cross-instinct desires)
- Gaps: Mass Instincts with few or no identified desires (potential untapped angles)
```

## Output Destination

Save to `clients/{client}/research/desire-research-{YYYY-MM-DD}.md`
