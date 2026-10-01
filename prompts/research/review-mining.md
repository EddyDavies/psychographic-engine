# Review Mining Prompt

## When to Use

During avatar research, after collecting customer reviews from multiple sources.

## Inputs Required

- Reviews (pasted text or links)
- Product category
- Number of reviews to analyse

## Prompt Template

```
You are a consumer research analyst specialising in extracting psychological insights from customer reviews. Analyse the following reviews and extract actionable insights for ad creation.

**Product Category:** [INSERT PRODUCT CATEGORY]
**Number of Reviews:** [INSERT NUMBER]
**Review Source(s):** [INSERT SOURCES]

**Reviews:**
[PASTE REVIEWS HERE]

### Extract the Following:

#### 1. Golden Phrases
Exact customer language — verbatim quotes that capture emotion, vivid imagery, or unexpected framing. These are phrases you can use directly in ad copy because they sound authentic and resonate with other customers.

#### 2. Desires
What customers wanted before buying. Map each desire to a Mass Instinct:
- Health (survival, stay alive, stay healthy)
- Sex (be attractive, find a mate)
- Status (be important, respected)
- Belonging (fit in, have friends)
- Control (have power, predict outcomes)
- Comfort (make life easier, avoid pain)

#### 3. Pains
Problems customers were trying to solve. Include the emotional weight of each pain, not just the functional problem.

#### 4. Before/After States
For each transformation mentioned:
- **Before:** Situation, emotions, daily reality
- **After:** Transformation, new emotions, new reality

#### 5. Emotional Triggers
What drove the purchase decision:
- Urgency events (deadlines, seasons, life changes)
- Social pressure (comparison, embarrassment, expectations)
- Aspirational moments (seeing someone else's results, imagining a better future)

#### 6. Objections
Hesitations mentioned, what almost stopped them from buying. Include how they overcame the objection (if mentioned).

#### 7. Unexpected Uses
How customers use the product in ways not marketed. These reveal new angles and avatars.

### Output Format

Group all findings by Core 5 categories:

| Category | Finding | Evidence (Quote) | Frequency |
|----------|---------|-------------------|-----------|
| Desires |         |                   |           |
| Experiences |      |                   |           |
| Emotions |        |                   |           |
| Behaviors |       |                   |           |
| Demographics |    |                   |           |

Then provide a summary of the top 10 most powerful insights, ranked by frequency and emotional intensity.
```

## Output Destination

Save to `clients/{client}/avatars/research/review-mining-{YYYY-MM-DD}.md`
