# Local typed-decision incident study — protocol v1

Written before model evaluation on the study dataset. This is a local,
content-hashed protocol freeze, not a registered study or an externally
independently timestamped preregistration. No TypeSafe model is evaluated.

## Question and scope

Can the public English Laya checkpoint generalize across unseen synthetic fault
mechanisms, follow explicit evidence rules, resist label-preserving distractors,
and identify a useful subset of decisions for automatic routing?

Primary comparison: raw Laya versus a supervised word/character TF-IDF logistic
classifier, measured by all-three-label exact accuracy averaged equally across
eight conditions within a mechanism and then across 36 held-out mechanisms.
The supervised comparator has task-specific training; this is a comparison of
practical local systems, not equal-training-data model capabilities.

No p-value or result is guaranteed. The design improves precision and controls;
statistical significance is a possible result, not the design's objective.

## Dataset and independence

72 hand-authored mechanisms, 24 per known owner. Each has eight conditions:
clean, paraphrase, irrelevant historical context, embedded contradictory
instructions, missing owner, missing impact, unresolved conflicting impact,
and explicitly resolved. Labels come from an explicit deterministic runbook
oracle, not a model judge. The 20 proof-of-concept cases are excluded.

Splits (seed 20261002, stratified by owner, grouped by mechanism):
- train: 24 mechanisms / 192 records;
- development: 12 mechanisms / 96 records;
- test: 36 mechanisms / 288 records.

All transformations of a mechanism stay together. Clean/paraphrase/distractor/
injection share labels. Missing/contradictory/resolved conditions change the
specified labels. Eight variants do not imply eight independent observations.
The test's effective replication unit is a fault mechanism (n=36), not a row
(n=288). Condition wording is shared across splits: this measures generalization
to unseen mechanisms within a fixed synthetic template distribution, not to
unseen writing styles, real incidents, or the full space of possible causes.
Missing-owner headings provide an unverified topic, never demonstrated ownership.

The authoring agent also authored the oracle and code. Mechanical integrity and
rule-consistency audits are performed, but no independent human label review is
claimed. Export a blinded review sheet for future independent review. Any label
corrections after test evaluation require a new version and disclosure.

## Frozen systems

1. Original keyword comparator (unchanged from proof of concept).
2. Per-field training majority; empirical training class proportions.
3. TF-IDF (word 1–2 grams and character-within-word 3–5 grams), logistic regression
   per output, L2 regularization C selected from {0.1,1,10} on development exact
   accuracy. Ties choose the smaller C. Vocabulary/IDF and coefficients fit on
   training only. No refit on development or test.
4. Raw Laya checkpoint revision 55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851, runtime
   laya 0.3.20, original proof-of-concept runbook and question wording unchanged.
5. Post-hoc temperature-scaled Laya: one scalar per output chosen on development
   NLL over a prespecified log-spaced grid [0.25,4] with 81 points. Rescale the
   checkpoint's returned rounded probabilities (clip at 1e-8), not original
   logits; this limitation is reported. No fine-tuning, test temperature fitting,
   or prompt search. Argmax labels must remain identical.

No local generative LLM comparator is included in v1. That is a future expansion,
not an implicit claim that decision models outperform local LLMs.

## Inference

In-process CPU inference with downloaded local weights. Disable Hugging Face
network access and socket connections. No inference API, server, or credentials.
Use four Torch threads, a fixed warmup on a training incident, batch size one,
and identical question/criterion order. Use a fixed criterion-order argmax to resolve ties in rounded probabilities. Retain raw probabilities, predicted
labels, model identity, data/prompt/code/weights hashes, latency, and exceptions.
Reject any input that would truncate evidence or criteria. Predictions receive
only runbook and incident. Never give labels, split, or variant to the model.
Resume only when manifest and source hashes match. No silent retries or dropped
cases. Any inference error blocks the final analysis until explicitly resolved.

Freeze artifacts before inference. Run development first, fit calibration and
routing policy, write its hash, then run test. Test labels may be read by the
analysis code only after test predictions are complete. Generation and mechanical
integrity checks necessarily access oracle labels before this point.

## Outcomes and statistics

Primary endpoint: all-three exact accuracy difference, raw Laya minus TF-IDF.
Report a 95% percentile paired cluster-bootstrap CI (10,000 resamples; seed
20261002), resampling mechanisms with all eight conditions together. Report a
prespecified two-sided cluster sign-flip permutation p-value (20,000 draws,
plus-one correction). The sign-flip test assumes exchangeability of system
labels at the cluster level under the null; no causal interpretation is claimed.
This is the only confirmatory comparison in this controlled study. All other
comparisons are descriptive, with no uncorrected significance claims.

Secondary: per-field accuracy and macro-F1, multiclass Brier score (sum over
classes then mean over records), clipped NLL, equal-width 10-bin ECE (descriptive;
small-bin instability), reliability tables, confusion matrices, condition-level
accuracy, and clean-to-transformed paired changes. Conditional attack flip rate
uses only clean-correct mechanisms; also show unconditional accuracy differences.
Calibrated versus raw Brier improvement gets a paired cluster CI, descriptively.

Precision planning: at n=36 independent families, a worst-case binary proportion
has about +/-16 percentage points normal-approximation 95% uncertainty. For a
paired family difference SD=0.5, a normal approximation gives ~23 percentage
points detectable at 80% power and two-sided alpha 0.05. This is a sensitivity
calculation under assumptions, not achieved/post-hoc power. Shared templates and
nonrandom authored mechanisms limit even those generalizations.

## Selective routing

Evidence must be sufficient and owner/impact known. Gate on the minimum of the
three selected probabilities. Tune a single threshold for each probabilistic
system on development using grid 0.00,0.01,...,1.00: maximize coverage subject to
empirical all-three error <=5%, at least 20 routed development records, and at
least five distinct development mechanisms. Ties select the larger threshold.
If none qualifies, disable automatic routing. Threshold selection uses point
estimates, not a safety guarantee or a certified risk bound. Test is untouched.

Report test coverage and routed error rate, routed sample and family counts,
and clustered bootstrap intervals where estimable; null rate if no routes.
All-reject can be safe but useless. Report critical-impact recall over all cases
separately, so withholding routes cannot hide missed high-impact incidents.
Show risk/coverage curves as descriptive plots, never pick a new threshold on test.
Keyword policy uses sufficient/known labels with no invented probabilities.

## Reporting and stopping

Complete every frozen case; do not stop because of accuracy or p-values. Stop
only for runtime errors, then fix implementation with an amendment and record
whether predictions were already inspected. Keep development-only changes
separate from test-result-driven changes. No publication or website edits here.
Produce a local report, JSON metrics, audit manifests, CSV review sheet, and
standalone scientific plots. State synthetic scope, the task-trained baseline,
shared templates, finite family count, and lack of independent human review.

Sources:
- Group-disjoint evaluation: https://scikit-learn.org/stable/modules/cross_validation.html
- Paired bootstrap: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
- Temperature scaling: https://proceedings.mlr.press/v70/guo17a.html
