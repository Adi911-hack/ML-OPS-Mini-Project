
INDIAN_AIRPORTS = {
    "DEL", "BOM", "BLR", "MAA", "HYD", "CCU",
    "COK", "GOI", "GOX", "PNQ", "AMD", "JAI",
    "LKO", "PAT", "BBI", "GAU", "IXC", "IXB",
    "IXR", "IXM", "TRV", "CCJ", "VNS", "SXR",
    "IXJ", "IDR", "NAG", "VTZ", "IXE", "IXZ",
    "RPR", "BHO", "ATQ", "IXA", "IXD", "IXL",
    "IXS", "IXU", "UDR", "JDH", "DED", "DIB"
}

KNOWN_FOREIGN_AIRPORTS = {
    "FRA", "CDG", "LHR", "LGW", "AMS", "FCO",
    "MUC", "ZRH", "JFK", "EWR", "LAX", "SFO",
    "ORD", "DXB", "AUH", "DOH", "SIN", "HKG",
    "BKK", "KUL", "SYD", "MEL", "YYZ", "YVR"
}


def check_regulatory_scope(claim):
    origin = str(claim.get("origin") or "").strip().upper()
    destination = str(claim.get("destination") or "").strip().upper()

    if not origin or not destination:
        return {
            "status": "unknown",
            "reason": (
                "Origin and destination are required to verify "
                "whether the route is covered by the supplied "
                "DGCA regulatory corpus."
            )
        }

    if origin in INDIAN_AIRPORTS or destination in INDIAN_AIRPORTS:
        return {
            "status": "supported",
            "reason": (
                "The flight operates within India or to/from "
                "India, consistent with DGCA CAR clauses "
                "1.1 and 1.2."
            )
        }

    if (
        origin in KNOWN_FOREIGN_AIRPORTS
        and destination in KNOWN_FOREIGN_AIRPORTS
    ):
        return {
            "status": "outside",
            "reason": (
                "Route outside supplied corpus: neither airport "
                "is in India. Indian DGCA compensation provisions "
                "must not be applied to this claim."
            )
        }

    return {
        "status": "unknown",
        "reason": (
            "Route applicability could not be verified using "
            "the available airport reference data. "
            "Human jurisdiction review is required."
        )
    }
