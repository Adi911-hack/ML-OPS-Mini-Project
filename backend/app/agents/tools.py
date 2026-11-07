
import json
from langchain_core.tools import tool


def create_claim_tools(claim):
    @tool
    def get_claim_fields(field_names: list[str]) -> str:
        """Get selected fields from the current passenger claim."""
        data = claim.model_dump(mode="json")
        result = {}

        for name in field_names:
            if name in data:
                result[name] = data[name]

        return json.dumps(result)

    return [get_claim_fields]


def create_entitlement_tools(claim, search_function=None, clause_function=None):
    @tool
    def get_claim_fields(field_names: list[str]) -> str:
        """Read fields from the current passenger claim."""
        return json.dumps({
            name: claim.get(name)
            for name in field_names
            if name in claim
        })

    @tool
    def search_corpus(query: str) -> str:
        """Search DGCA and airline documents for applicable rules and exceptions."""
        if search_function is None:
            return json.dumps({
                "status": "unavailable",
                "passages": [],
                "reason": "The real DGCA retrieval system is not connected."
            })

        return json.dumps(search_function(query))

    @tool
    def get_clause_by_id(clause_id: str) -> str:
        """Retrieve the source passage for an exact clause identifier."""
        if clause_function is None:
            return json.dumps({
                "status": "unavailable",
                "clause": None,
                "reason": "The real clause lookup system is not connected."
            })

        return json.dumps(clause_function(clause_id))

    return [get_claim_fields, search_corpus, get_clause_by_id]
