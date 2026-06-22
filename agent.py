"""
FitFindr planning loop — orchestrates tools with session state.
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


def _parse_query(query: str) -> dict:
    """Extract description, size, and max_price from natural language query."""
    text = query.strip()
    max_price = None
    size = None

    price_patterns = [
        r"under\s*\$?\s*(\d+(?:\.\d+)?)",
        r"below\s*\$?\s*(\d+(?:\.\d+)?)",
        r"max\s*\$?\s*(\d+(?:\.\d+)?)",
        r"less than\s*\$?\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            max_price = float(match.group(1))
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            break

    size_match = re.search(r"\bsize\s+([A-Za-z0-9/]+)", text, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).strip(",.")
        text = re.sub(
            r"\bsize\s+" + re.escape(size_match.group(1)),
            "",
            text,
            flags=re.IGNORECASE,
        )

    description = re.sub(r"\s+", " ", text).strip(" ,.")
    if not description:
        description = query.strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed

    results = search_listings(
        parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    if not results:
        size_note = parsed["size"] or "any"
        price_note = (
            f"${parsed['max_price']:.0f}"
            if parsed["max_price"] is not None
            else "no limit"
        )
        session["error"] = (
            f"No listings found for '{parsed['description']}' "
            f"(size: {size_note}, max price: {price_note}). "
            f"Try broadening your search — remove the size filter, "
            f"raise your price limit, or use different keywords."
        )
        return session

    session["selected_item"] = results[0]

    outfit = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit

    if not outfit or not outfit.strip():
        session["error"] = (
            "Could not generate an outfit suggestion. Please try again."
        )
        return session

    session["fit_card"] = create_fit_card(outfit, session["selected_item"])
    return session


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
