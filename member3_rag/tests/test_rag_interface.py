
from pathlib import Path
import re
import pymupdf
import pytest

from member3_rag.rag_interface import (
    get_clause_by_id,
    search_corpus,
    DOCUMENTS_DIR
)
from member3_rag.process_documents import clean_text


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def normalize_source(text):
    text = clean_text(text)

    text = re.sub(
        r"CIVIL AVIATION REQUIREMENTS\s+SERIES\s*[‘'\"`]M[’'\"`]\s*PART IV\s+SECTION 3\s+6TH AUGUST, 2010\s+\d+\s+Rev\.\s*4,\s*dated\s*25th Jan,\s*2023",
        " ",
        text,
        flags=re.IGNORECASE
    )

    return normalize(text)


@pytest.mark.parametrize("clause_id,page", [
    ("DGCA:3.2.2", 4),
    ("DGCA:3.3.2", 5),
    ("DGCA:3.4.2", 6),
    ("DGCA:3.4.4", 6),
    ("DGCA:3.5.1", 6)
])
def test_clause_exists(clause_id, page):
    result = get_clause_by_id(clause_id)

    assert result is not None
    assert result["clause_id"] == clause_id
    assert result["page"] == page
    assert result["source"] == "dgca_car_section3_series_m_part4.pdf"
    assert result["text"].strip()


@pytest.mark.parametrize("clause_id", [
    "DGCA:3.2.2",
    "DGCA:3.3.2",
    "DGCA:3.4.2",
    "DGCA:3.4.4",
    "DGCA:3.5.1"
])
def test_text_matches_original_pdf(clause_id):
    result = get_clause_by_id(clause_id)

    assert result is not None

    pdf_path = DOCUMENTS_DIR / result["source"]

    with pymupdf.open(pdf_path) as pdf:
        original = "\n".join(
            page.get_text("text") for page in pdf
        )

    original = normalize_source(original)
    retrieved = normalize_source(result["text"])

    assert retrieved in original


def test_six_hour_delay_clause():
    result = get_clause_by_id("DGCA:3.4.2")

    assert result is not None

    text = result["text"].lower()

    assert "more than 6 hrs" in text
    assert "alternate flight" in text
    assert "full refund" in text
    assert "3.4.3" not in text


def test_extraordinary_circumstances_clause():
    result = get_clause_by_id("DGCA:3.4.4")

    assert result is not None

    text = normalize(result["text"]).lower()

    assert "para 1.4 and para 1.5" in text
    assert "reasonable measures" in text
    assert "3.4.5" not in text


def test_invalid_clause():
    result = get_clause_by_id("DGCA:99.99.99")

    assert result is None


def test_search_returns_relevant_clause():
    results = search_corpus(
        "Domestic flight delayed more than six hours, alternate flight or refund",
        top_k=5
    )

    assert len(results) > 0
    assert any(
        item["clause_id"] == "DGCA:3.4.2"
        for item in results
    )


def test_search_lookup_consistency():
    results = search_corpus(
        "Compensation for flight cancellation"
    )

    assert results

    for item in results:
        clause = get_clause_by_id(item["clause_id"])

        assert clause is not None
        assert clause["text"] == item["text"]
        assert clause["source"] == item["source"]
        assert clause["page"] == item["page"]


def test_response_structure():
    results = search_corpus("Denied boarding compensation")

    assert results

    for item in results:
        assert set(item) == {
            "clause_id",
            "source",
            "page",
            "text",
            "distance"
        }

        assert isinstance(item["clause_id"], str)
        assert isinstance(item["source"], str)
        assert isinstance(item["page"], int)
        assert isinstance(item["text"], str)
        assert isinstance(item["distance"], float)
