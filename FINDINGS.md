# First local run — 2026-10-02

The proof of concept runs end to end on CPU without an API, server, or key.
Python socket connections were blocked for model loading and the entire 20-case
run. The actual model is **convaiinnovations/laya**, pinned to revision
`55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, with runtime `laya==0.3.20`.
This is not TypeSafe Jev and provides no evidence about TypeSafe Jev performance.

| Metric | Laya | Keyword baseline |
|---|---:|---:|
| Owner correct | 13/20 | 17/20 |
| Current impact correct | 10/20 | 17/20 |
| Evidence quality correct | 17/20 | 14/20 |
| All three correct | 6/20 | 13/20 |

Laya median per-incident inference time was 1.52 seconds on CPU (three questions
per incident); p95 nearest rank was 1.63 seconds. These include token-budget
checks and the first inference, exclude model loading, and are not GPU speed
measurements. No state or question was truncated.

At the untuned 0.90 selected-probability threshold, the gate sent **20/20 cases
to review**. Zero automated recommendations means there is no measured automated
routing error rate; it does not establish successful automation.

Interesting errors:

- Embedded ticket instructions changed database/degraded into network/critical.
- A staging-only incident with an alarming title was classified critical.
- A report with no useful observations received critical impact and sufficient evidence.
- Temporal correlation with a deployment was treated as established application ownership.

These are useful cases to inspect, not broad vulnerability or reliability claims.
The small synthetic set was authored alongside the baseline and is exploratory.
Prompts and thresholds were not revised after observing these model predictions.
A blog-ready evaluation needs separate development and test sets, independent
label review, and a local LLM comparator before drawing general conclusions.

Possible blog angle: **Can a Tiny Local Decision Model Triage an Incident?**
The story here is how a typed answer can be valid while its decision is wrong,
and how a cautious probability gate can prevent all automation rather than
magically make a model useful.

## Artifacts and reproduction

- `results/laya-offline/report.md`: metrics and per-case predictions.
- `results/laya-offline/results.jsonl`: raw model outputs and routing decisions.
- `results/laya-offline/summary.json`: configuration, hashes, and metrics.
- `results/laya-offline/requests.json`: exact model inputs without gold labels.
- `results/baseline/report.md`: comparator results.

```bash
.venv/bin/python verify_offline.py
.venv/bin/python triage.py --backend baseline
python3 -m unittest -v
```

The Laya runtime warned that its checkpoint's temperature for questions with 11+
options was clamped. Our questions have three or four options, so that temperature
bucket is not used. This does not establish calibration for our task.
