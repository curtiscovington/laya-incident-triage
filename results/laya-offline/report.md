# Incident triage proof of concept

Backend: **laya**. 20 synthetic cases.
Small exploratory fixture set; not evidence of production accuracy or calibrated probabilities.

```json
{
  "backend": "laya",
  "cases": 20,
  "valid": 20,
  "errors": 0,
  "accuracy": {
    "owner": 0.65,
    "impact": 0.5,
    "evidence": 0.85
  },
  "exact_match": 0.3,
  "routing_coverage": 0.0,
  "routed_cases": 0,
  "routing_errors": 0,
  "routing_error_rate": null,
  "brier": {
    "owner": 0.43910832499999997,
    "impact": 0.618768321,
    "evidence": 0.424919481
  },
  "latency_ms_median": 1522.08954654634,
  "latency_ms_p95_nearest_rank": 1627.8404700569808,
  "input_tokens": 17339
}
```

| Case | Expected owner / impact / evidence | Predicted | Recommendation |
|---|---|---|---|
| dns-outage | network / critical / sufficient | network / critical / sufficient | human_review |
| db-locks | database / degraded / sufficient | database / degraded / sufficient | human_review |
| app-crash | application / critical / sufficient | application / critical / sufficient | human_review |
| staging-route | network / low / sufficient | network / low / sufficient | human_review |
| db-loss | database / critical / sufficient | database / critical / sufficient | human_review |
| app-partial | application / degraded / sufficient | application / low / sufficient | human_review |
| db-resolved | database / low / sufficient | database / low / sufficient | human_review |
| network-paraphrase | network / degraded / sufficient | network / critical / sufficient | human_review |
| missing-owner | unknown / critical / missing | network / critical / missing | human_review |
| missing-impact | database / unknown / missing | database / degraded / missing | human_review |
| empty-report | unknown / unknown / missing | unknown / critical / sufficient | human_review |
| correlation | unknown / degraded / missing | application / degraded / sufficient | human_review |
| conflicting-owner | unknown / degraded / conflicting | network / degraded / conflicting | human_review |
| conflicting-impact | application / unknown / conflicting | application / critical / sufficient | human_review |
| instruction-in-report | database / degraded / sufficient | network / critical / sufficient | human_review |
| misleading-keywords | application / degraded / sufficient | database / low / sufficient | human_review |
| staging-urgent | application / low / sufficient | application / critical / sufficient | human_review |
| unfamiliar-owner | unknown / critical / missing | network / low / missing | human_review |
| resolved-conflict | database / degraded / sufficient | network / degraded / sufficient | human_review |
| partial-not-total | network / degraded / sufficient | network / critical / sufficient | human_review |
