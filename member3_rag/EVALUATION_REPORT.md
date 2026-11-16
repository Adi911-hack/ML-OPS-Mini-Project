# Member 3 — RAG and Agent Evaluation Report

## 1. Overview

This module evaluates the retrieval and evidence-grounding performance of the Air Passenger Compensation Claim Triage System.

The RAG system retrieves relevant regulations from DGCA Civil Aviation Requirements, IndiGo Conditions of Carriage, and the Ministry of Civil Aviation Passenger Charter.

The evaluation covers regulatory retrieval accuracy, citation integrity, claim-level evidence, and the reliability of AI-generated recommendations.

## 2. Evaluation Dataset

The evaluation dataset contains 21 scenarios.

File: `claim_evaluation_cases.json`

Categories covered:

- Flight delays
- Flight cancellations
- Denied boarding
- Downgrading
- Extraordinary circumstances
- Missing evidence
- Out-of-scope claims

Each scenario contains:

- Scenario ID
- Category
- Passenger claim
- Expected regulatory clauses
- Expected outcome
- Expected decision route

### Mandatory Scenarios

SC06 covers the assignment's Section 4.1 cancellation scenario.

The passenger receives cancellation notice 90 minutes before departure and accepts an alternative flight four hours later.

Expected outcome under the assignment scenario:

- No cancellation compensation.
- Meals and refreshments while waiting.

SC21 covers an EU flight cancellation between Paris and Berlin.

Expected outcome:

- Identify that EU Regulation EC 261/2004 is outside the available Indian regulatory corpus.
- Do not invent EU compensation amounts.
- Do not apply Indian DGCA regulations to an unrelated EU claim.
- Refer the case for appropriate review.

SC19 additionally evaluates an out-of-scope railway claim.

The dataset contains 21 scenarios, of which 19 have expected Indian regulatory clause references. The remaining two are out-of-corpus scenarios.

Expected outcomes and routes are provisional evaluation labels and must be checked against the final decision-routing rules.

## 3. RAG Implementation

The retrieval system uses:

- PyMuPDF for PDF text extraction.
- Sentence Transformers for semantic embeddings.
- ChromaDB for vector storage and retrieval.
- Clause-level indexing for regulatory references.
- Exact clause lookup for citation verification.

The current corpus contains 87 indexed passages.

Available integration functions:

`search_corpus(query, top_k=5)`

`get_clause_by_id(clause_id)`

## 4. Retrieval Evaluation

Evaluation command:

```powershell
python -m member3_rag.evaluate_claims --top-k 5
```

Latest measured results:

| Metric | Result |
|---|---:|
| Total scenarios | 21 |
| Scored retrieval scenarios | 19 |
| Expected clause references | 29 |
| Retrieved expected references | 17 |
| Clause Recall@5 | 58.62% |
| All-clauses hit rate | 47.37% |
| Mean Reciprocal Rank | 0.3741 |
| Missing reference IDs | 0 |

Recall@5 measures the proportion of expected regulatory clause references appearing among the top five retrieved results.

These values measure retrieval performance, not the correctness of final compensation decisions.

## 5. Citation Integrity Evaluation

Evaluation command:

```powershell
python -m member3_rag.evaluate_citation_integrity
```

Results:

| Metric | Result |
|---|---:|
| Total scenarios | 21 |
| Retrieved passages checked | 105 |
| Verified passages | 105 |
| Rejected original passages | 0 |
| Citation integrity | 100% |
| Tampering rejection | 100% |

Citation integrity compares each retrieved passage with its corresponding record in the ChromaDB index.

Tampering rejection tests whether deliberately altered passage text is detected.

These results demonstrate consistency with the indexed corpus. They do not independently establish that the indexed text is legally correct or that generated answers are faithful.

## 6. L2 — Prompt Version Comparison

Two prompt versions are planned.

### v1-basic

A basic regulatory evidence-retrieval prompt.

The agent identifies relevant regulations and retrieves supporting passages for the passenger claim.

### v2-exception-aware

An enhanced retrieval prompt that explicitly considers:

- Relevant regulatory conditions
- Cancellation notice periods
- Alternate flight acceptance
- Extraordinary circumstances
- Compensation exclusions
- Missing evidence
- Applicable passenger assistance

The same 21-scenario dataset will be evaluated using both versions.

Every response must record the actual prompt version used.

The comparison will report:

- Groundedness
- Context relevance
- Faithfulness
- Hallucination rate
- Per-metric differences between versions

Prompt implementation is being coordinated with Person 2.

Status: Pending real prompt-version runs.

## 7. L3 — Four Evaluation Metrics

The following metrics are calculated using saved agent responses and human-reviewed annotations.

### 7.1 Groundedness

Measures the percentage of factual claims in the agent's answer that are supported by retrieved regulatory evidence.

Formula:

Groundedness = Supported factual claims / Total factual claims

Higher is better.

### 7.2 Context Relevance

Measures the percentage of distinct retrieved passages that are relevant to the passenger's question.

Formula:

Context relevance = Relevant retrieved passages / Total distinct retrieved passages

Higher is better.

### 7.3 Faithfulness

Measures the percentage of factual claims that accurately represent the meaning and conditions of the supporting evidence.

Formula:

Faithfulness = Faithful factual claims / Total factual claims

Higher is better.

### 7.4 Hallucination Rate

Measures the percentage of factual claims that cannot be supported by the retrieved evidence.

Formula:

Hallucination rate = Unsupported factual claims / Total factual claims

Lower is better.

Under these definitions, hallucination rate equals one minus groundedness.

This relationship is a consequence of the chosen binary annotation method, not an independent measurement.

### Annotation Method

For each completed agent response:

1. Identify individual factual claims in the recommendation and reasoning.
2. Inspect the retrieved regulatory passages.
3. Record which passages are relevant to the passenger's question.
4. Mark each factual claim as supported or unsupported.
5. Mark whether the claim faithfully represents the supporting evidence.
6. Record the completed review.
7. Calculate the four metrics.

Missing or incomplete reviews are excluded from scoring and reported separately.

Cases without factual claims receive N/A for claim-level metrics.

The evaluation uses an explicit human-annotation method rather than TruLens.

## 8. Batch Evaluation

Batch evaluator:

`evaluate_agent_batch.py`

Scoring script:

`evaluate_metrics.py`

The batch evaluator is designed to:

- Run the same scenarios for both prompt versions.
- Record the selected prompt version.
- Save outputs after every scenario.
- Resume incomplete runs.
- Stop safely when the Gemini API reports rate-limit or service errors.
- Preserve retrieved passages and citation-verification information.

The evaluator requires Person 2's versioned-prompt update.

### Example Commands

Run one scenario after installing the prompt-version update:

```powershell
python -m member3_rag.evaluate_agent_batch --version v1-basic --limit 1 --delay 0
```

Run all scenarios for the basic prompt:

```powershell
python -m member3_rag.evaluate_agent_batch --version v1-basic
```

Run all scenarios for the exception-aware prompt:

```powershell
python -m member3_rag.evaluate_agent_batch --version v2-exception-aware
```

Prepare review files:

```powershell
python -m member3_rag.evaluate_metrics --prepare v1-basic
python -m member3_rag.evaluate_metrics --prepare v2-exception-aware
```

After completing the annotations, calculate metrics:

```powershell
python -m member3_rag.evaluate_metrics --score v1-basic
python -m member3_rag.evaluate_metrics --score v2-exception-aware
```

Compare versions:

```powershell
python -m member3_rag.evaluate_metrics --compare
```

Results must not be presented as complete until all required scenarios have been evaluated and reviewed.

## 9. Before-and-After Comparison

The deliberate experimental change is the prompt switch from `v1-basic` to `v2-exception-aware`.

The dataset and evaluation definitions remain unchanged.

| Metric | v1-basic | v2-exception-aware | Difference |
|---|---|---|---|
| Groundedness | Pending | Pending | Pending |
| Context relevance | Pending | Pending | Pending |
| Faithfulness | Pending | Pending | Pending |
| Hallucination rate | Pending | Pending | Pending |

The comparison will identify which prompt performs better and quantify the difference in percentage points.

No real four-metric comparison results are available yet.

## 10. Current Limitations

1. Retrieval Recall@5 is 58.62%, indicating that some expected clauses are missing from the top five results.
2. Exact citation matching does not independently verify the legal accuracy of retrieved documents.
3. Person 2's prompt-version support is required before running the full comparison.
4. The existing entitlement reasoner supports cancellation cases more fully than other disruption types.
5. Agent responses may conservatively request further evidence.
6. Expected scenario outcomes require validation against the final routing implementation.
7. Human review is required to annotate evidence relevance and factual support.
8. Gemini API limits may require evaluation runs to be spaced out.

## 11. Completed Work

- 21 evaluation scenarios created.
- Mandatory 4.1 and EU out-of-corpus cases included.
- 87 regulatory passages indexed.
- 16 automated RAG interface tests passed.
- Retrieval evaluation completed.
- Citation integrity evaluation completed.
- Tampering detection evaluation completed.
- Resumable batch evaluator implemented.
- Four-metric scoring script implemented.
- Synthetic scoring test passed.

## 12. Remaining Work

- Integrate Person 2's two prompt versions.
- Run both prompts across the 21 scenarios.
- Complete factual-claim and passage-relevance annotations.
- Calculate the four required metrics for both versions.
- Report before-and-after differences.
- Validate the mandatory 4.1 and EU cases against actual agent decisions.
- Include reviewed results in the final project report.
- Open a pull request for Docker integration testing.
- Obtain Aryaman's approval before merging into main.

## 13. Conclusion

The RAG retrieval and citation-verification components have been implemented and tested.

The current results establish retrieval performance and citation consistency.

The final L2 and L3 requirements will be complete only after both prompt versions have been executed on the fixed evaluation dataset, the four required metrics have been measured, and the before-and-after comparison has been documented.
## Final L2 Prompt-Version Comparison

### Evaluation Setup

Two entitlement prompt versions were evaluated:

- v1-basic
- v2-exception-aware

The evaluation dataset contains 21 scenarios covering airline disruption claims and regulatory edge cases.

Gemini 503 fallback runs were tracked separately and excluded from the direct prompt comparison.

### Evaluation Results

| Metric | v1-basic | v2-exception-aware |
|---|---|---|
| Total scenarios in dataset | 21 | 21 |
| Valid non-fallback runs recorded | 18 | 11 |
| Comparable non-fallback scenarios | 11 | 11 |
| Expected regulatory clauses retrieved | 11/16 | 12/16 |
| Expected-clause recall | 68.75% | 75.00% |

The comparable scenarios were SC01, SC02, SC03, SC04, SC05, SC06, SC07, SC11, SC12, SC13, and SC14.

The v2-exception-aware prompt achieved a 6.25 percentage-point improvement in expected-clause retrieval recall over v1-basic.

### Observations

1. Both prompt versions successfully retrieved relevant DGCA regulatory passages.
2. The v2-exception-aware prompt retrieved one additional expected clause across the 11 comparable scenarios.
3. Several scenarios produced request-further-evidence recommendations because the entitlement assessment was limited or information was missing.
4. Gemini 503 errors caused some runs to use fallback retrieval.
5. Retrieved regulatory evidence was evaluated separately from citations supporting the final entitlement decision.
6. The comparison does not establish that v2 produces more accurate entitlement decisions.

### Limitations

- The direct comparison includes 11 valid paired scenarios, rather than all 21.
- The v2-exception-aware evaluation had only reached scenario SC15.
- Groundedness, context relevance, faithfulness, and hallucination rate require completed evidence-level annotations; final numerical values are not yet established.
- Further evaluation is required before claiming a statistically reliable improvement in overall decision quality.

### Conclusion

The exception-aware prompt demonstrated better expected-clause retrieval recall on the available paired scenarios (75.00% versus 68.75%).

The evaluation also identified limitations in automated entitlement reasoning and intermittent Gemini service availability.

These results provide preliminary evidence of improved retrieval coverage, but not a verified improvement in final compensation decisions.