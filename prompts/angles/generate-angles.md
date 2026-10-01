# Generate Angles (Agent Workflow)

## When to Use

Step 2 of the pipeline (`prompts/README.md`) when an agent has repo access. It runs the angle extraction from `angle-generation.md` for one sub-avatar on one offer, writes the angle files, and keeps `ranked-angles.md` current.

Run it when:

- A sub-avatar is new, or its `confidence` rose
- A new product or offer was added
- `prompts/testing/process-learnings.md` retired an angle and the sub-avatar has fewer than three untested angles on that offer

## Not For

- Choosing formats, messaging concepts, or visual concepts (that is Step 4 and Step 5)
- Writing angle briefs (that is `angle-brief.md`)

## Read First

1. `clients/{client}/concepts/angles-and-testing.md`, the niche gap test in `clients/{client}/avatars/README.md`, the market sophistication sections of `concepts/marketing-frameworks.md`, `concepts/belief-framework.md`, and the hooks section of `concepts/copywriting.md`
2. The sub-avatar profile (`avatars/core-{name}/sub-{name}/profile.md`) and its parent core profile
3. The offer: `products/{slug}.md` or `offers/{slug}.md` (claims, mechanisms, assumed benefits); method in `concepts/offer-understanding.md`
4. `strategy/awareness-levels.md` (awareness per sub-avatar, sophistication stage, chosen response)
5. `avatars/core-{name}/ranked-angles.md` and the existing angle files for that sub-avatar
6. `testing/learnings.md` and `testing/creative-tracker.csv`
7. `brand/no-gos/no-gos.md`

## Steps

1. **Re-run the niche gap test** on the sub-avatar and update its `Three Questions` line. If any answer is no, stop and report the overlap (which sub-avatar, and why) instead of writing angles.
2. **List the sub-avatar's most painful or specific attributes** for the chosen offer: implied beliefs, objections, experiences, emotions.
3. **Turn attributes into reasons to buy.** For each attribute, ask "what reason to buy does this give?" Keep the ones a media buyer could repeat in one sentence. Discard anything that describes a format or a test. Drop any reason that violates a belief the sub-avatar holds, or that rests on a bigger claim instead of the sophistication response recorded in `awareness-levels.md` (new mechanism, new information, or new identity). Skip any reason already captured in an existing angle file or retired in `learnings.md`.
4. **Write three angle files** from `clients/_template/avatars/core-TEMPLATE/sub-TEMPLATE/angle-TEMPLATE.md` at `avatars/core-{name}/sub-{name}/angle-{slug}.md`, strongest first.
   - Frontmatter: `type: angle`, `sub_avatar`, `offer` (slug of the products/ or offers/ file), `status: untested`, `strength` (1 to 3, 1 strongest), `updated` (today).
   - **Reason to Buy:** one sentence.
   - **Emotional Lever:** the profile line that makes it land.
   - **Proof Points:** only claims the offer file supports, each with its source. Never fabricate.
   - **Objections to Pre-empt:** from the profile's Objections section, each with how the ad handles it.
   - If the sub-avatar supports more than three strong angles, report the extras in your summary; they get promoted when an angle retires.
5. **Hooks.** Follow the pipeline in `prompts/README.md`: hooks are born at ad assembly (Step 5), so leave the angle file's Hooks placeholders and the ranked-angles `Hook:` line as pending. Whenever hooks are written, check each against `concepts/copywriting.md`: about 5 words (3 to 7), two lines at most on a phone; one of the two hook frameworks (biggest thing happening now, or quirky); at least three of the Four U's with Unique present. Across three hooks, aim for one from the mechanism, one from new information, and one that validates the pain in the customer's words. If the sub-avatar is unaware, the hook must not name the problem.
6. **Check against the no-gos.** Every reason to buy and proof point must pass `brand/no-gos/no-gos.md`.
7. **Update `ranked-angles.md`.** Put the angles under `# Offer: {slug}`, rank the sub-avatars by strength within that offer, keep one block per angle in the exact format the template shows (`**Angle N: Name**`, `Reason to Buy:`, `Hook:`, `-> [full angle](...)`; `scripts/generate-ads.py` parses it), and update the Testing Priority.
8. **Validate.** Run `uv run python scripts/check-knowledge.py` and fix every error before handing back. Commit in your private copy; never add client data to this public template.

## Worked Example (Fernwood)

Review: "I switched to an eco spray last year and my windows have never looked worse. Back to the old stuff."

- Sub-avatar: `sub-let-down-eco-switcher` (tried a green alternative, it failed her, she went back)
- Offer: `starter-kit`
- Niche gap: different ad (it has to prove the clean, not the planet); unique objection ("eco products never clean as well"); situation alone (she already switched once and switched back). Three yeses.
- Most painful attribute: the experience "eco spray smeared the glass" and the belief it left behind
- Reason to Buy: the starter kit cleans glass streak-free from one pod and tap water, so going green no longer means a worse clean
- Emotional Lever: the let-down of the first switch, which she blames on eco products in general
- Proof Points: "Streak-free on glass" and "plant-based formula" (both from `products/{slug}.md`)
- Objection to pre-empt: "Eco products never clean as well": answered by showing the glass, not by claiming
- Angle file: `avatars/core-low-waste-household/sub-let-down-eco-switcher/angle-proves-it-actually-cleans.md`
- First test: Discovery batch, concept `c01`, static, `avatar-callout` visual concept
