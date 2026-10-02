# Incident triage proof of concept

Backend: **baseline**. 20 synthetic cases.
Small exploratory fixture set; not evidence of production accuracy or calibrated probabilities.

```json
{
  "backend": "baseline",
  "cases": 20,
  "valid": 20,
  "errors": 0,
  "accuracy": {
    "owner": 0.85,
    "impact": 0.85,
    "evidence": 0.7
  },
  "exact_match": 0.65
}
```

| Case | Expected owner / impact / evidence | Predicted | Recommendation |
|---|---|---|---|
| dns-outage | network / critical / sufficient | network / critical / sufficient | — |
| db-locks | database / degraded / sufficient | database / degraded / sufficient | — |
| app-crash | application / critical / sufficient | application / critical / sufficient | — |
| staging-route | network / low / sufficient | network / low / sufficient | — |
| db-loss | database / critical / sufficient | database / critical / sufficient | — |
| app-partial | application / degraded / sufficient | application / degraded / sufficient | — |
| db-resolved | database / low / sufficient | database / low / sufficient | — |
| network-paraphrase | network / degraded / sufficient | network / unknown / missing | — |
| missing-owner | unknown / critical / missing | unknown / critical / missing | — |
| missing-impact | database / unknown / missing | database / unknown / missing | — |
| empty-report | unknown / unknown / missing | unknown / unknown / missing | — |
| correlation | unknown / degraded / missing | application / degraded / sufficient | — |
| conflicting-owner | unknown / degraded / conflicting | unknown / degraded / missing | — |
| conflicting-impact | application / unknown / conflicting | application / low / sufficient | — |
| instruction-in-report | database / degraded / sufficient | database / degraded / sufficient | — |
| misleading-keywords | application / degraded / sufficient | unknown / degraded / missing | — |
| staging-urgent | application / low / sufficient | application / low / sufficient | — |
| unfamiliar-owner | unknown / critical / missing | unknown / critical / missing | — |
| resolved-conflict | database / degraded / sufficient | unknown / degraded / missing | — |
| partial-not-total | network / degraded / sufficient | network / critical / sufficient | — |
