
# Member 3 — RAG Module

This module retrieves relevant DGCA regulations and airline passenger policies for the Air Passenger Compensation Claim Triage Service.

## Source documents

The documents folder contains:

- dgca_car_section3_series_m_part4.pdf
- indigo_conditions_of_carriage.pdf
- moca_passenger_charter.pdf

Sources:
- DGCA: https://www.dgca.gov.in/
- IndiGo: https://www.goindigo.in/information/conditions-of-carriage.html
- Ministry: https://www.civilaviation.gov.in/

The DGCA reference currently used is Revision 4, dated 25 January 2023. Check for amendments before using it for current claims.

## Setup from project root

Create and activate a virtual environment on Windows:

    py -m venv .venv
    .\.venv\Scripts\Activate.ps1

Install dependencies:

    python -m pip install -r member3_rag/requirements.txt

Build the clause-level ChromaDB index:

    python -m member3_rag.rag_interface --build

## Available functions

    from member3_rag.rag_interface import search_corpus, get_clause_by_id

    results = search_corpus("What if my flight is delayed?")
    clause = get_clause_by_id("DGCA:3.4.2")

search_corpus() returns a list of dictionaries containing clause_id, source, page, text and distance.

get_clause_by_id() returns clause_id, source, page and text, or None when not found.

## Run tests

    python -m pytest member3_rag/tests/test_rag_interface.py -v

## Notes

The ChromaDB index is generated locally and is not committed to Git.

Clause extraction is preliminary. Retrieved passages must be verified against the source documents before final entitlement recommendations.

The original chunk-level evaluation and clause-level evaluation are separate.
