# Blog framing notes (methods, not a draft result)

Working title: **Can a Small Local Decision Model Triage an Incident?**

Open with the distinction that motivated the experiment: restricting a model's
outputs to a known set prevents invalid labels, but does not establish that its
chosen label is true. This project tests the independent open-weight Laya model,
not the hosted TypeSafe Jev model that inspired the interface.

The experiment should be presented as a controlled synthetic stress test:

1. Define ownership, current impact, and evidence quality, with unknown explicitly
   allowed. Show a clean incident and a minimally changed ambiguous version.
2. Explain why 576 variants are only 72 mechanism families, with 36 held out.
   All related variants stay together, so rewrites do not multiply sample size.
3. Describe the practical baselines. The TF-IDF model has task-specific labeled
   training and shares the generator's condition vocabulary; Laya is used without
   task fine-tuning. That asymmetry is part of the experiment and must be visible.
4. Show the primary paired difference and interval before condition anecdotes.
5. Separate probability calibration from classification: temperature scaling may
   improve probability quality without changing a single chosen label.
6. Explain coverage and error together. A system that escalates everything has
   no observed automatic-routing errors, but has automated nothing.
7. Close with what remains unknown: real incident prevalence and wording,
   independently checked labels, unfamiliar owner categories, and comparisons
   with local generative LLMs or other decision models.

Avoid claims that this establishes production reliability, proves anything about
TypeSafe Jev, or demonstrates a model's behavior on arbitrary incident prose.
Do not pick only interesting failed examples after seeing results; retain the
condition table and complete raw outputs alongside selected examples.

The final numerical claims must come from artifacts/REPORT.md and metrics.json.
Figures are generated as standalone PNG and SVG files for export. No website or
public post is modified by this study.
