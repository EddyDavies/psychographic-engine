# Angles and Testing

The vocabulary every angle file, test plan, and tracker row uses. Based on the Evolve framework.

## Definitions

| Term | Meaning | Fernwood example |
|---|---|---|
| **Concept** (batch concept) | The big idea of one ad set, numbered. Contains one or more angles. | `c01`: "Discovery across three low-waste household sub-avatars" |
| **Angle** | The reason one sub-avatar buys one offer. One sentence a media buyer could repeat back. | "The refill pods clean as hard as the bottle you gave up, so switching costs you nothing." |
| **Variation** | One execution of an angle: a hook, a headline, a cut. | Hook 2 of that angle on an annotated lifestyle visual |
| **Format** | How it is delivered: static, video, carousel, email (see `formats/`). | Static |
| **Testing method** | Discovery Batch, Deep Iteration, or A/B Split (see `prompts/testing/methods.md`). | Discovery Batch |

### Concept versus messaging and visual concepts

`prompts/concepts/messaging/` and `prompts/concepts/visual/` hold **messaging concepts** and **visual concepts**. They are treatments applied at ad assembly, and they are always named with their qualifier. A bare "concept" in a test plan or in the `concept` column of `testing/creative-tracker.csv` always means the batch concept above.

## One concept is one ad set: the 3:2:2 rule

Each concept runs as one ad set holding **three creatives** (the variations), **two primary texts**, and **two headlines**.

- **Discovery Batch** (Evolve's "Marksman"): the concept is "test these angles", so each of the three creatives carries a different angle with one variation each.
- **Deep Iteration** (Evolve's "Sniper"): the three creatives are three executions of one angle. Same reason to buy, different ways to say or show it.

Ad assembly writes one primary text and one headline per creative. For the ad set, pick the strongest two of each.

### A format change is its own concept

Do not mix a format test into an angle test in the same ad set. It adds a second variable, and the result cannot be read. A format test (including the strategy or execution check in `execution.md`) gets its own ad set and its own concept number, and still names the angle it carries. Visual concepts are treatments, not formats: three visual concepts on one angle in one static ad set is still a single concept.

## What makes an angle

- It gives the customer a reason to buy. If it does not, it is a format or a messaging concept, not an angle.
- It comes from the sub-avatar's most painful or specific attribute: an implied belief, an objection, an experience, an emotion.
- It is specific enough to write ads from. "Wants a greener home" is too broad. "Your refill cupboard is full of eco sprays that smear the glass; these don't" is an angle.
- Bad angles: "us vs them", "before and after", "problem aware ads". Those describe how you test, not why they buy.
- Every ad has an angle, even when the batch is testing a format.
- An angle belongs to one offer. The same reason to buy on the starter kit and on a single refill pack is two angle files, because the proof points and objections change.

## Hooks

Hooks communicate the angle. Direct, not indirect. Each hook works as the headline of a static or the first line of a video. Hook rules (length, the Four U's, the three hook sources) are in `copywriting.md`. When hooks are written is set by the pipeline in `prompts/README.md`.

## Ranked angles

`avatars/core-{name}/ranked-angles.md` groups angles by offer, ranks sub-avatars by strength within each offer, and sets the testing priority: strongest sub-avatar, angle 1, first hook first. Layer supporting angles into body copy rather than testing every angle separately.

## The testing loop

Discovery first for direction. Deep Iteration second on the angle that earns spend. Discovery again when a Deep Iteration angle plateaus. Bulk content seeding (Evolve's "Shotgun") is a content strategy, not a test, and is never used for strategy work.

## Hook and hold rule for video

Hooks call out the specific sub-avatar ("POV: you swapped to eco spray and the windows still smear"). The hold demonstrates the core avatar's shared mechanism (one concentrated pod, mixed with tap water, cleans like the bottle you used to buy). Keep hooks specific and the hold generic enough to serve every hook in the batch. Once the platform shows which hook wins, run Deep Iteration on the hold for that sub-avatar.

## Learnings

A learning names the sub-avatar, the angle, and the offer, and says why. "Lifestyle visuals beat studio shots" is a format observation; the learning also records which reason to buy the winning visual carried. Before marking an angle a loser, run the strategy or execution diagnostic in `execution.md`. The full close-the-loop steps are in `prompts/testing/process-learnings.md`.

Related: `../avatars/README.md` (Core 5 and the niche gap test), `copywriting.md`, `execution.md`, `marketing-frameworks.md`.
