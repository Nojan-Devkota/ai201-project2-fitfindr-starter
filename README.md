# FitFindr

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. It searches mock listings, suggests outfits based on your wardrobe, and generates a shareable fit card caption.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Run tests:

```bash
pytest tests/
```

Run the agent CLI:

```bash
python agent.py
```

## Tool Inventory

### search_listings

| | |
|---|---|
| **Purpose** | Search mock listings by keywords, size, and price |
| **Inputs** | `description` (str), `size` (str \| None), `max_price` (float \| None) |
| **Returns** | `list[dict]` — matching listings sorted by relevance, or `[]` if none match |

Each listing dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`.

### suggest_outfit

| | |
|---|---|
| **Purpose** | Suggest outfit combinations using a thrift find and the user's wardrobe |
| **Inputs** | `new_item` (dict), `wardrobe` (dict with `items` list) |
| **Returns** | `str` — outfit suggestion or general styling advice |

Uses Groq `llama-3.3-70b-versatile`.

### create_fit_card

| | |
|---|---|
| **Purpose** | Generate a casual, shareable social media caption |
| **Inputs** | `outfit` (str), `new_item` (dict) |
| **Returns** | `str` — 2–4 sentence caption, or an error message if outfit is empty |

Uses Groq `llama-3.3-70b-versatile` at temperature 0.9 for varied output.

## Planning Loop

The agent uses a conditional planning loop in `agent.py`:

1. **Parse query** — Regex extracts `description`, `size`, and `max_price` from natural language (e.g., "under $30", "size M").
2. **Search** — Calls `search_listings` with parsed params.
3. **Branch on results** — If empty, sets `session["error"]` with actionable advice and stops. Does not call downstream tools.
4. **Select item** — Sets `session["selected_item"]` to the top search result.
5. **Suggest outfit** — Calls `suggest_outfit(selected_item, wardrobe)`. Stops if suggestion is empty.
6. **Create fit card** — Calls `create_fit_card(outfit_suggestion, selected_item)`.
7. **Return session** — All results stored in the session dict for the UI.

The loop responds to tool output — it does not call all three tools unconditionally.

## State Management

A `session` dict tracks one interaction:

- `parsed` — extracted search parameters
- `search_results` — full result list from search
- `selected_item` — top listing, passed to `suggest_outfit` and `create_fit_card`
- `outfit_suggestion` — string from `suggest_outfit`, passed to `create_fit_card`
- `fit_card` — final caption
- `error` — set on early termination

State flows automatically: the item found by search becomes the input to outfit suggestion, which becomes the input to the fit card — no re-entry needed.

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No matches | Error in listing panel: suggests broadening keywords, removing size filter, or raising price limit. Outfit and fit card panels stay empty. |
| `suggest_outfit` | Empty wardrobe | Returns general styling advice instead of crashing. Agent continues to fit card. |
| `create_fit_card` | Empty outfit string | Returns `"Cannot create a fit card without an outfit suggestion. Run suggest_outfit first."` |

**Example (tested):** Query `"designer ballgown size XXS under $5"` returns no listings. Agent shows: *"No listings found for 'designer ballgown' (size: XXS, max price: $5). Try broadening your search..."* — no outfit or fit card is generated.

**Example (tested):** `create_fit_card("", item)` returns the error string above without raising an exception.

## Interaction Walkthrough

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."

**Step 1 — search_listings**
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Output: List of matches; top result is *Vintage Band Tee — Faded Grey*, $19 on depop

**Step 2 — suggest_outfit**
- Input: selected band tee + example wardrobe (baggy jeans, chunky sneakers, etc.)
- Output: Outfit pairing the tee with wardrobe pieces and styling tips

**Step 3 — create_fit_card**
- Input: outfit suggestion + band tee listing
- Output: Casual Instagram-style caption mentioning the tee, price, and platform

**Final output:** Three UI panels — listing details, outfit idea, and fit card caption.

## Spec Reflection

**One way planning.md helped during implementation:**

Writing the conditional branches in the Planning Loop section before coding made the agent structure straightforward. Knowing that an empty search result must stop the flow prevented accidentally calling `suggest_outfit` with no item — a common agent bug.

**One divergence from the spec, and why:**

The spec mentioned picking size "M" from queries like "size M", but some example queries omit explicit size (e.g., "vintage graphic tee under $30"). The parser leaves `size=None` in those cases rather than guessing, which returns more results and matches how users actually search.

## AI Usage

**Instance 1 — Tool implementations**

- **Input:** Tool 1–3 spec blocks from `planning.md` (inputs, returns, failure modes) plus `load_listings()` signature
- **Produced:** `search_listings`, `suggest_outfit`, and `create_fit_card` in `tools.py`
- **Revised:** Added `_fallback_outfit_advice()` for LLM failures and ensured size matching uses substring logic so "M" matches "S/M"

**Instance 2 — Planning loop**

- **Input:** Architecture diagram and Planning Loop + State Management sections from `planning.md`
- **Produced:** `run_agent()` with regex query parsing and conditional branches
- **Revised:** Added explicit check for empty outfit suggestion before calling `create_fit_card`; error messages include parsed filter values for clearer user feedback

## Project Structure

```
├── agent.py           # Planning loop and session state
├── app.py             # Gradio UI
├── tools.py           # Three agent tools
├── planning.md        # Design spec (written before implementation)
├── tests/test_tools.py
├── data/
│   ├── listings.json
│   └── wardrobe_schema.json
└── utils/data_loader.py
```
