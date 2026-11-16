# Member 3 — Offline Evaluation Review (Partial)

The saved runs are **not** a complete human annotation of 21 paired scenarios. Do not report the preliminary factual-support scores as overall system performance.

## Comparable non-fallback subset

Paired IDs: SC01, SC02, SC03, SC04, SC05, SC06, SC07, SC11, SC12, SC13, SC14 (11 pairs).

| Metric | v1-basic | v2-exception-aware |
|---|---:|---:|
| Expected-clause recall | 11/16 (68.75%) | 12/16 (75.00%) |
| Expected-clause *precision proxy* across retrieved passages (macro average) | 14.97% | 14.00% |
| Scenarios with checked factual assertions in paired subset | 2/11 | 1/11 |
| Factual assertions checked | 6 | 3 |
| Groundedness on checked assertions only | 100% | 100% |
| Faithfulness on checked assertions only | 100% | 100% |
| Hallucination rate on checked assertions only | 0% | 0% |

The context-relevance proxy uses only the assignment's expected clause IDs as relevant; it does **not** replace expert relevance judgements about other retrieved passages. The factual-claim figures cover SC05 and SC06 in v1 and SC06 in v2, not the full paired set. The equal 100% figures cannot be used to rank models, as only a tiny, nonrepresentative selection was reviewed.

The operational response “Automated entitlement assessment currently supports cancellation claims only” is not a substantive regulatory assertion. These rows remain **unreviewed**, rather than assigning misleading `supported=true` labels or fabricating claims. Generic evidence-request or human-escalation responses likewise need a defined rubric for handling zero substantive factual assertions. Several cases return an escalation instead of the expected entitlement result.

## Provided files

- `v1-basic_reviews.json`: relevant clause ID matches populated; factual assertions reviewed for SC05, SC06, and SC08 (the latter is outside the paired subset).
- `v2-exception-aware_reviews.json`: relevant clause ID matches populated; factual assertions reviewed for SC06.
- `partial_metrics.json`: machine-readable preliminary metrics and counts.

All other scenarios preserve `review_complete: false`. The project's existing scorer deliberately refuses to score such cases. Do not set them to `true` without substantive review, and do not present partial figures as the required completed L2/L3 four-metric evaluation.
