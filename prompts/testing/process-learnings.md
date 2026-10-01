# Process Learnings (Agent Workflow)

## When to Use

Close the loop after a batch: flip angle status, write the learning that names the sub-avatar, angle, and offer, and queue what to test next. This is the "Processing Results" step in `methods.md`, run as a checklist.

Run it when:

- A batch has hit the decision rule in its test plan (minimum spend and success criteria from `test-plan-template.md`)
- Weekly while a test is live

## Read First

1. The batch's test plan: success criteria and minimum spend before judging
2. The results the user provides (ad platform export or report)
3. `clients/{client}/testing/creative-tracker.csv` and `testing/learnings.md`
4. `clients/{client}/concepts/execution.md` and `concepts/angles-and-testing.md`
5. The angle files and `ranked-angles.md` for every angle in the batch
6. Comments on the winning and losing ads, if the user can share them

## Steps

1. **Call each row.** For each tracker row with `status` `testing`, set `status` to `winner` or `loser` per the decision rule and fill `result` with the key metrics (spend, CPA or ROAS, CTR). Note CTR against the soft benchmark in `execution.md` (at least 1%); it is a guide, never the verdict.
2. **Strategy or execution?** Before retiring an angle, apply the diagnostic in `execution.md`. Filter the tracker by `angle` and read `format`: has the angle been tried in more than one format?
   - Every format lost: record a **strategy** loss.
   - One format gave a direction: record an **execution** loss and keep the angle.
   - Only one format tried: record an **execution** loss for now and plan a format test as its own concept.
   - For a loser, check it against the thirteen execution failure reasons and name the likely one in `notes`.
3. **Update each angle file.** Set `status` and `updated` in the frontmatter, and add a Test History line: concept id, date, result, why. For a winner, record the winning hook in the Hooks section with `inspired_by: test result, {concept id}`.
4. **Write the learning** in `learnings.md`. Add a Winners or Losers row with sub-avatar, angle, offer, format, key metric, and (for losers) the loss type. Then add a Key Learnings line that says why in psychographic terms: which belief, experience, or objection the hook hit or missed. A format-only observation is not enough; record the reason to buy it carried.
5. **Retire deliberately.** Move an angle to Retired Angles only on a strategy loss, or after three losing batches where execution was the suspected cause (`execution.md`, how long to keep an angle). Set its `status: loser`.
6. **Feed the profile.** If the sub-avatar behind a winner is unclear, mine the ad's comments and any new reviews for Core 5 statements, save them under `avatars/research/`, and add them to the right sub-avatar profile with the file in `sources`. Raise `confidence` one step (low to medium, medium to high) only when the new material adds at least two verbatim quotes. If a comment describes a situation no sub-avatar covers, run the niche gap test before creating one.
7. **Re-rank.** Update `strength` in the angle files and the order in `ranked-angles.md` if the results changed the ranking.
8. **Queue what comes next** in Next Directions:
   - A winner still improving: Deep Iteration on it.
   - Everything lost, or a Deep Iteration angle plateaued: a new Discovery batch.
   - An execution loss on an avatar you are confident in: a second batch on that angle (Deep Iteration, or a different format), and a third only if the feedback still points at execution. After three losing batches, move to another angle.
   - A sub-avatar left with fewer than three untested angles on an offer: run `prompts/angles/generate-angles.md`.
9. **Refresh coverage.** Update the Coverage Summary in `testing/creative-tracker.md`.
10. **Validate.** Run `uv run python scripts/check-knowledge.py` and fix every error. Commit in your private copy; never add client data to this public template.

## Worked Example (Fernwood)

Concept `c01`, a Discovery batch on the `starter-kit` offer: three static creatives, one angle each, from three sub-avatars of `core-low-waste-household`.

- `proves-it-actually-cleans` (`sub-let-down-eco-switcher`): 2.3% CTR, lowest CPA in the set. Winner.
- `cupboard-space-back` (`sub-flat-share-no-storage`): 0.6% CTR. Only ever run as a static: execution loss, likely reason 1 (no emotional impact). Keep the angle; plan a video format test as its own concept.
- `refill-not-reorder` (`sub-subscription-sceptic`): lost as a static in `c01` and as a video in `c02`. Strategy loss. Retire it and run generate-angles for that sub-avatar.

Learning: "`sub-let-down-eco-switcher` responds to proof that the clean is as good as before, not to the planet. The hook hit her experience of eco spray smearing the glass. Next: Deep Iteration on `proves-it-actually-cleans`, three executions of the glass demo."
