# Dataset and implementation audit

Completed before the final test run. This is an author audit, not independent
human annotation or an external scientific review.

## Automated checks

- 576 records and 72 mechanism families; exactly eight conditions per family.
- 24/12/36 train/development/test families; no family appears in two splits.
- No exact duplicated incident text across the three splits.
- Clean, paraphrase, distractor and injection labels are identical within family.
- Missing-owner conditions require unknown owner and missing evidence.
- Missing-impact conditions require unknown impact and missing evidence.
- Conflicting-impact conditions require unknown impact and conflicting evidence.
- Resolved conditions require low current impact.
- Input-only projections contain ID and incident, with no gold label or condition.
  Prediction payload construction passes only incident and the common runbook.
- Metrics reject missing/duplicate prediction IDs and malformed distributions.
- Unit checks verify that duplicating rows within a family does not narrow the
  family-bootstrap interval, and identical systems have zero paired gap and p=1.
- Routing tests cover minimum record/family support, evidence overrides, disabled
  policies, and null risk when no cases are routed.

## Author review of the construction

The mechanisms span 24 network faults, 24 database faults, and 24 application
faults. Ownership is tied to the demonstrated subsystem, not the symptom word:
for example a routing-table bug in application code belongs to application,
whereas a router forwarding loop belongs to network. Explicit environment and
current-impact observations override the apparent severity of a fault mechanism.
An unverified alert heading in missing-owner cases is not a root-cause finding.
Resolved cases explicitly establish current healthy production; they are not
scored on historical impact. Conflicting cases explicitly leave monitor reports
unresolved. Embedded instructions are identified as comments, not observations.

## Remaining threats to validity

- Closely related semantic mechanisms and shared condition phrasing remain,
  despite no identical records or shared family IDs. Group isolation is not proof
  of semantic independence or absence of template learning.
- All labels and prose came from the same authoring process; no external incident
  corpus, blinded independent adjudication, or measured inter-rater agreement.
- Ownership and impact categories are intentionally narrow. No general-purpose
  incident taxonomy, multi-owner resolution, or operational dispatch is tested.
- Training proportions and challenge prevalence are engineered, not sampled from
  real on-call traffic. Selected routing rates do not predict deployment volume.
- Model predictions have three related fields; they are not three independent
  tests per incident. The primary endpoint evaluates them jointly.

Use the generated blinded review CSV for a later independent annotation pass.
Any corrections after predictions exist must be versioned and reported.
