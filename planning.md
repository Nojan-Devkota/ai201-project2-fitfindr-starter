# FitFindr — planning.md

> Complete this document before writing any implementation code.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for secondhand items matching a keyword description, optional size, and optional max price. Returns matches ranked by keyword relevance.

**Input parameters:**
- `description` (str): Keywords describing what the user wants (e.g., "vintage graphic tee").
- `size` (str | None): Size filter; case-insensitive substring match against listing size (e.g., "M" matches "S/M"). None skips size filtering.
- `max_price` (float | None): Maximum price inclusive. None skips price filtering.

**What it returns:**
A `list[dict]` of matching listing dicts, sorted by relevance (highest score first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns `[]` if nothing matches — never raises.

**What happens if it fails or returns nothing:**
The agent sets `session["error"]` with a message listing what was searched and suggests loosening filters (try a different size, raise the price cap, or broaden keywords). It returns early without calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
Uses Groq (llama-3.3-70b-versatile) to suggest 1–2 complete outfit combinations pairing a thrift find with pieces from the user's wardrobe, or general styling advice if the wardrobe is empty.

**Input parameters:**
- `new_item` (dict): A listing dict from `search_listings` (the item being considered).
- `wardrobe` (dict): Wardrobe with an `items` key — list of wardrobe item dicts (`id`, `name`, `category`, `colors`, `style_tags`, `notes`).

**What it returns:**
A non-empty `str` with outfit suggestions (specific wardrobe piece names when wardrobe exists, or general pairing advice when empty).

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty, the tool still returns general styling advice (does not crash). If the LLM call fails, returns a fallback string with basic pairing tips based on the item's category and style tags. The agent stores the result in `session["outfit_suggestion"]` and continues to `create_fit_card` unless the string is empty.

---

### Tool 3: create_fit_card

**What it does:**
Uses Groq (llama-3.3-70b-versatile, temperature 0.9) to generate a short, casual Instagram/TikTok-style caption for the outfit and thrift find.

**Input parameters:**
- `outfit` (str): The outfit suggestion string from `suggest_outfit`.
- `new_item` (dict): The listing dict for the thrifted item.

**What it returns:**
A `str` — 2–4 sentence shareable caption mentioning item name, price, and platform naturally. If `outfit` is empty or whitespace-only, returns an error message string (no exception).

**What happens if it fails or returns nothing:**
If outfit input is missing, returns: `"Cannot create a fit card without an outfit suggestion. Run suggest_outfit first."` The agent stores this in `session["fit_card"]` or sets `session["error"]` if outfit was also missing upstream.

---

## Planning Loop

**How does your agent decide which tool to call next?**

1. Parse the user query with regex to extract `description`, `size`, and `max_price`. Store in `session["parsed"]`.
2. Call `search_listings(**parsed)`. Store results in `session["search_results"]`.
3. **Branch:** If `search_results` is empty → set `session["error"]` with actionable advice → return session (stop).
4. Set `session["selected_item"] = search_results[0]`.
5. Call `suggest_outfit(selected_item, wardrobe)`. Store in `session["outfit_suggestion"]`.
6. **Branch:** If outfit suggestion is empty → set `session["error"]` → return session (stop).
7. Call `create_fit_card(outfit_suggestion, selected_item)`. Store in `session["fit_card"]`.
8. Return session.

The loop is conditional: steps 5–7 only run when search succeeds. Step 7 only runs when outfit suggestion is non-empty.

Query parsing uses regex (documented choice) — no LLM needed for parsing. Patterns: `under $N`, `size M`, etc.

---

## State Management

**How does information from one tool get passed to the next?**

A single `session` dict is initialized per interaction via `_new_session()`. Fields:

| Field | Set when | Used by |
|-------|----------|---------|
| `parsed` | Step 2 (query parse) | `search_listings` |
| `search_results` | After search | Selecting top item |
| `selected_item` | After search success | `suggest_outfit`, `create_fit_card` |
| `outfit_suggestion` | After suggest | `create_fit_card` |
| `fit_card` | After fit card | Final output |
| `error` | On early exit | UI error display |

No re-prompting: `selected_item` from search flows directly into `suggest_outfit`; `outfit_suggestion` flows into `create_fit_card`.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | `"No listings found for '<description>' (size: X, max price: $Y). Try broadening your search — remove the size filter, raise your price limit, or use different keywords like 'graphic tee' instead of a specific band name."` Agent stops; outfit and fit card panels stay empty. |
| suggest_outfit | Wardrobe is empty | Tool returns general styling advice (e.g., "Pair this band tee with baggy jeans and chunky sneakers for a 90s grunge look"). Agent continues to fit card. |
| create_fit_card | Outfit input is missing or incomplete | Tool returns `"Cannot create a fit card without an outfit suggestion. Run suggest_outfit first."` Agent shows this in the fit card panel or sets error if outfit was never generated. |

---

## Architecture

```
User query
    │
    ▼
Planning Loop ───────────────────────────────────────────────┐
    │                                                        │
    ├─ Parse query → session["parsed"]                       │
    │                                                        │
    ├─► search_listings(description, size, max_price)        │
    │       │ results=[]                                     │
    │       ├──► [ERROR] helpful message → return session    │
    │       │                                                │
    │       │ results=[item, ...]                            │
    │       ▼                                                │
    │   session["selected_item"] = results[0]              │
    │       │                                                │
    ├─► suggest_outfit(selected_item, wardrobe)              │
    │       │ empty wardrobe → general advice                │
    │       ▼                                                │
    │   session["outfit_suggestion"] = "..."                 │
    │       │                                                │
    └─► create_fit_card(outfit_suggestion, selected_item)    │
            │ empty outfit → error string                    │
            ▼                                                │
        session["fit_card"] = "..."                          │
            │                                                │
            ▼                                                │
        Return session ◄─────────────────────────────────────┘
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

- **Tool:** Cursor AI
- **Input:** Tool 1 spec block (inputs, return value, failure mode) + `load_listings()` signature from `utils/data_loader.py`
- **Expected output:** `search_listings()` with keyword scoring, price/size filters, empty list on no match
- **Verification:** Run 3 queries manually — vintage graphic tee (hits), designer ballgown XXS $5 (empty), jacket under $10 (price filter). Run pytest.

**Milestone 4 — Planning loop and state management:**

- **Tool:** Cursor AI
- **Input:** Architecture diagram + Planning Loop + State Management sections
- **Expected output:** `run_agent()` with conditional branches and session dict updates
- **Verification:** Run `python agent.py` — happy path prints title/outfit/fit card; no-results path prints error and leaves fit_card None.

---

## A Complete Interaction (Step by Step)

FitFindr takes a natural language thrift request, searches listings, styles the top match against the user's wardrobe, and generates a shareable fit card. Each tool runs only when the previous step succeeds; search failure stops the flow with actionable feedback.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
Agent parses query → `description="vintage graphic tee"`, `size=None`, `max_price=30.0`.
Calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`.
Returns 3+ matches; top result: **Vintage Band Tee — Faded Grey**, $19, depop, size L.
Stores in `session["search_results"]` and `session["selected_item"]`.

**Step 2:**
Calls `suggest_outfit(selected_item, example_wardrobe)`.
LLM pairs the band tee with "Baggy straight-leg jeans" and "Chunky white sneakers" from the wardrobe.
Returns outfit suggestion string. Stores in `session["outfit_suggestion"]`.

**Step 3:**
Calls `create_fit_card(outfit_suggestion, selected_item)`.
LLM generates a casual caption mentioning the tee, $19, depop, and the outfit vibe.
Stores in `session["fit_card"]`.

**Final output to user:**
- **Listing panel:** Vintage Band Tee — Faded Grey, $19, depop, Good condition, size L
- **Outfit panel:** Pair with baggy jeans and chunky sneakers for a 90s grunge look...
- **Fit card panel:** "thrifted this faded band tee off depop for $19 and honestly it was made for my wide-legs 🖤"

**Error path:** If search returns nothing, user sees the error message in the listing panel only — no outfit or fit card is generated.
