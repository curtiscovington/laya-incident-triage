The first visual inspection found that a legend overlapped condition bars.
`study/render_figures.py` was added after numerical analysis as a presentation-only
pass: it reads metrics.json and risk-coverage.json, uses the identical measurements,
moves legends outside axes, and formats axes as percentages. It asserts that the
metrics file remains unchanged. The frozen inference/analysis sources and all
numeric outcomes remain unchanged. Run it after `study/run.py analyze` to reproduce
these layouts. Original layouts remain reproducible through the frozen analyzer.
