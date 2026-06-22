"""
FitFindr tools — search, outfit suggestion, and fit card generation.
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

MODEL = "llama-3.3-70b-versatile"


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _call_llm(prompt: str, temperature: float = 0.7) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _score_listing(listing: dict, keywords: list[str]) -> int:
    if not keywords:
        return 0

    text_parts = [
        listing.get("title", ""),
        listing.get("description", ""),
        listing.get("category", ""),
        listing.get("brand") or "",
        " ".join(listing.get("style_tags", [])),
        " ".join(listing.get("colors", [])),
    ]
    combined = " ".join(text_parts).lower()
    return sum(1 for kw in keywords if kw in combined)


def _matches_size(listing_size: str, target_size: str) -> bool:
    return target_size.upper() in listing_size.upper()


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """Search mock listings by keywords, optional size, and max price."""
    listings = load_listings()
    keywords = [
        word.lower()
        for word in re.findall(r"\w+", description)
        if len(word) > 1
    ]

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and not _matches_size(listing["size"], size):
            continue

        score = _score_listing(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


def _format_wardrobe_items(items: list[dict]) -> str:
    lines = []
    for item in items:
        tags = ", ".join(item.get("style_tags", []))
        colors = ", ".join(item.get("colors", []))
        note = item.get("notes") or ""
        lines.append(
            f"- {item['name']} ({item['category']}, {colors}, {tags}) {note}".strip()
        )
    return "\n".join(lines)


def _fallback_outfit_advice(new_item: dict) -> str:
    tags = ", ".join(new_item.get("style_tags", []))
    category = new_item.get("category", "piece")
    return (
        f"Style tip for this {category}: lean into its {tags or 'vintage'} vibe. "
        f"Pair with relaxed denim or wide-leg trousers and chunky sneakers or boots. "
        f"Keep accessories minimal so the {new_item.get('title', 'find')} stays the focus."
    )


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """Suggest outfits pairing a thrift find with the user's wardrobe."""
    items = wardrobe.get("items", [])
    title = new_item.get("title", "this item")
    description = new_item.get("description", "")
    tags = ", ".join(new_item.get("style_tags", []))

    try:
        if not items:
            prompt = (
                f"The user has no wardrobe saved yet. They are considering buying:\n"
                f"Title: {title}\nDescription: {description}\nStyle tags: {tags}\n\n"
                f"Suggest 1-2 complete outfit ideas using common basics "
                f"(e.g., baggy jeans, wide-leg pants, sneakers, boots). "
                f"Be specific about silhouette and vibe. Keep it under 120 words."
            )
        else:
            wardrobe_text = _format_wardrobe_items(items)
            prompt = (
                f"New thrift find:\nTitle: {title}\nDescription: {description}\n"
                f"Style tags: {tags}\n\nUser's wardrobe:\n{wardrobe_text}\n\n"
                f"Suggest 1-2 complete outfits using the new item plus specific "
                f"named pieces from their wardrobe. Include styling tips "
                f"(tuck, roll sleeves, layering). Keep it under 150 words."
            )

        result = _call_llm(prompt, temperature=0.7)
        if result:
            return result
    except Exception:
        pass

    return _fallback_outfit_advice(new_item)


def create_fit_card(outfit: str, new_item: dict) -> str:
    """Generate a shareable social caption for the outfit."""
    if not outfit or not outfit.strip():
        return (
            "Cannot create a fit card without an outfit suggestion. "
            "Run suggest_outfit first."
        )

    title = new_item.get("title", "thrift find")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "depop")

    prompt = (
        f"Write a casual Instagram/TikTok outfit caption (2-4 sentences).\n"
        f"Item: {title}\nPrice: ${price}\nPlatform: {platform}\n"
        f"Outfit: {outfit}\n\n"
        f"Sound like a real OOTD post — not a product listing. "
        f"Mention the item, price, and platform once each naturally. "
        f"Use a specific vibe. Emojis okay but don't overdo it."
    )

    try:
        return _call_llm(prompt, temperature=0.9)
    except Exception:
        return (
            f"scored this {title} for ${price} on {platform} and built the whole "
            f"fit around it — {outfit[:80]}..."
        )
