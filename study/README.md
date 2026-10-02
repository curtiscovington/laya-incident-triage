# Controlled local incident-triage study

This extends the original 20-case proof of concept into **576 synthetic records
from 72 fault mechanisms**, with grouped train/development/test splits. It tests
Laya, not TypeSafe Jev. Everything runs locally; no inference server, API, or key.

Read [the protocol](PROTOCOL.md) for the hypotheses, split, assumptions, analysis,
and stopping rule. The local [freeze manifest](FREEZE.json) binds source files,
datasets, environment, and weights before inference. It is not an externally
registered preregistration.

## Study arms

- Original keyword rules.
- Majority labels estimated from training only.
- Task-trained word/character TF-IDF logistic classifiers.
- Frozen public Laya English checkpoint.
- The same Laya outputs after development-only temperature calibration.

The learned classifier gets task training; Laya does not. We compare practical
systems and do not attribute differences solely to architecture. No local
generative LLM comparator is included in this version.

## Splits

| Split | Fault mechanisms | Records | Purpose |
|---|---:|---:|---|
| Train | 24 | 192 | Classifier fitting and a fixed model warmup |
| Development | 12 | 96 | Regularization, temperature and routing selection |
| Test | 36 | 288 | Final frozen evaluation |

Every mechanism has clean, paraphrase, distractor, injection, missing-owner,
missing-impact, conflicting-impact, and resolved variants. Keep all eight together
in every split and bootstrap sample. Templates are shared between splits; the
claim is held-out-mechanism generalization within this controlled distribution.
The effective test replication count is 36, not 288.

Gold labels come from a deterministic runbook oracle. `run.py audit` checks family
isolation, projection to label-free inputs, oracle invariants, and exact duplicates.
No independent human review has been done. A blinded review sheet is generated
for that next step; its existence is not evidence of completed review.

## Run / resume

From the project root, using the already installed local environment:

```bash
.venv/bin/python study/run.py audit
.venv/bin/python -m unittest discover -s study -p 'test_*.py' -v
.venv/bin/python study/run.py dev
.venv/bin/python study/run.py fit
.venv/bin/python study/run.py test
.venv/bin/python study/run.py analyze
.venv/bin/python study/render_figures.py
.venv/bin/python study/verify_results.py
```

Development/test inference resumes from flushed JSONL records and validates
source hashes. `fit` refuses to overwrite its selection or run after test inference
starts. Re-run `analyze` to reproduce figures and the report from saved predictions;
it performs no model inference. Do not rerun `freeze` on this existing study.
Changes to frozen code, data, prompts, or methods need a new version or an explicit
amendment; the runner intentionally refuses unnoticed changes.

On a new machine, follow the parent README's model setup, then install
`requirements-study.txt` from the project root. `study/environment.lock.txt`
records the full tested Linux ARM64 CPU environment. Hash checks validate source
and weights; they do not enforce an identical operating system or CPU. Pin the
environment for strict reproduction.

## Outputs

- `runs/laya-dev.jsonl` and `runs/laya-test.jsonl`: raw probabilities, model responses,
  token budgets and per-incident CPU latency. These contain no expected labels.
- `runs/selection.json`: development-selected regularization, temperatures and policies.
- `runs/tfidf.joblib`: trained local classifier, hashed in the selection file.
- `artifacts/REPORT.md`: results, uncertainty, failure analysis, limits and figures.
- `artifacts/metrics.json`: full metrics, confusion matrices, reliability bins,
  cluster intervals and paired comparisons.
- `artifacts/case-results.csv`: auditable model-level test decisions.
- `artifacts/blind-review.csv`: opaque IDs, incident text and empty review columns.
- `artifacts/*.png` and `*.svg`: standalone figures for the eventual blog.

Only the Laya-versus-TF-IDF exact-accuracy comparison is prespecified for inference.
Other comparisons and plots are descriptive. No model or threshold changes are
made in response to test results. No website changes or publishing occur here.
