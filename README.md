# FitFindr — Starter Kit

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to style it. Given a natural language request, the agent searches a mock listings dataset, suggests an outfit using the user's existing wardrobe, and generates a shareable social-media-style caption, handling failures gracefully at every step.

Run the interface:
```bash
python app.py
```

---

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) → list[dict]`
Searches the mock listings dataset for items matching the description, optional size, and optional price ceiling. Filters by max_price and size first, then scores remaining listings by keyword overlap between `description` and each listing's title, description, and style_tags. Returns matching listings sorted by relevance (highest score first), or an empty list if nothing matches.

### `suggest_outfit(new_item: dict, wardrobe: dict) → str`
Given a thrifted item and the user's wardrobe, uses the Groq LLM to suggest 1–2 complete outfit combinations using the new item alongside specific named pieces from the wardrobe. If the wardrobe is empty, falls back to general styling advice based on the new item's category, colors, and style_tags alone, it never crashes or returns an empty string.

### `create_fit_card(outfit: str, new_item: dict) → str`
Generates a short, casual, shareable caption (2–4 sentences) describing the outfit written in the voice of a real social media post rather than a product listing. Mentions the item, price, and platform naturally. Uses a high LLM temperature (0.95) so output varies across calls. Returns a descriptive error string if `outfit` is empty or missing, without calling the LLM.

---

## Planning Loop

The planning loop in `run_agent()` runs sequentially with conditional branching at two points:

1. The agent first parses the user's natural language query using the LLM, extracting `description`, `size`, and `max_price` into a structured dict (stored in `session["parsed"]`).
2. It calls `search_listings()` with those parsed values.
   - **If `search_results` is empty:** the agent sets `session["error"]` to a specific message telling the user what to adjust, and returns immediately. It does not call `suggest_outfit` or `create_fit_card`.
   - **If results exist:** the agent selects the top result (`session["selected_item"] = search_results[0]`) and continues.
3. It calls `suggest_outfit()` with the selected item and the user's wardrobe.
   - **If the result starts with "Could not generate":** the agent treats this as a failure, sets `session["error"]`, and returns early without calling `create_fit_card`.
   - **Otherwise:** the agent proceeds to the final step.
4. It calls `create_fit_card()` with the outfit suggestion and selected item, storing the result in `session["fit_card"]`.

The agent's behavior is not a fixed sequence, it branches based on what each tool actually returns. A query with no matching listings never reaches the outfit or fit card stages, and an empty wardrobe (a handled case, not a failure) flows through normally with general advice instead of specific wardrobe references.

---

## State Management

All state for a single interaction lives in one session dictionary, initialized at the start of `run_agent()` and threaded through every step:

| Key | Set by | Used by |
|-----|--------|---------|
| `query` | Initial input | `_parse_query()` |
| `parsed` | `_parse_query()` | `search_listings()` |
| `search_results` | `search_listings()` | Selecting `selected_item` |
| `selected_item` | Top result selection | `suggest_outfit()`, `create_fit_card()` |
| `wardrobe` | Initial input | `suggest_outfit()` |
| `outfit_suggestion` | `suggest_outfit()` | `create_fit_card()` |
| `fit_card` | `create_fit_card()` | Final output |
| `error` | Any failed/empty step | Early return check |

Each tool reads its inputs directly from the session dict rather than requiring the user to re-enter anything. For example, the listing found by `search_listings` is stored in `session["selected_item"]` and passed directly into `suggest_outfit` the user never has to describe the item a second time.

---

## Error Handling

| Tool | Failure mode | Agent response | Tested example |
|------|-------------|-----------------|-----------------|
| `search_listings` | No results match the query | Sets `session["error"]` to: *"No listings found matching your search. Try broadening your description, adjusting your size, or raising your max price."* Returns immediately — `suggest_outfit` and `create_fit_card` are never called. | Query: "designer ballgown size XXS under $5" → returned `[]`, agent stopped before calling the other two tools (see screenshot). |
| `suggest_outfit` | Wardrobe is empty | Does not raise an exception, generates general styling advice from the new item's own attributes (category, colors, style_tags) instead of referencing wardrobe pieces. This is treated as a normal case, not an error. | Tested with `get_empty_wardrobe()` on "vintage graphic tee under $30", returned general cottagecore styling advice instead of crashing; `session["error"]` remained `None`. |
| `create_fit_card` | Outfit input is empty or missing | Returns the string *"Could not generate a fit card — outfit description was missing."* without calling the LLM. | Tested directly with `create_fit_card('', results[0])` → returned the exact error string, confirmed via pytest. |

---

## Spec Reflection

**One way the spec helped me:** Writing out the exact session dict keys and the step-by-step branching logic in planning.md before touching `agent.py` made the implementation almost mechanical. I knew exactly what to check after each tool call (empty results? error prefix?) because I had already written the conditions down. When I gave Claude the Planning Loop and State Management sections as a prompt, the generated code matched my intended structure almost exactly, which made it quick to verify.

**One way my implementation diverged from the spec:** My original planning.md didn't specify exactly how the natural language query would be turned into `description`, `size`, and `max_price`, the starter `agent.py` flagged this as an open decision in step 2 of its TODO. I chose to use the LLM itself to parse the query into structured JSON rather than using regex, since natural phrasing like "under $30" or "size M" varies too much for reliable regex matching. This added a new helper function, `_parse_query()`, that wasn't in my original tool list, with a fallback to using the raw query as the description if JSON parsing fails.

---

## AI Usage

**Instance 1 - Implementing `search_listings`, `suggest_outfit`, and `create_fit_card`:**
I gave Claude each tool's spec block from planning.md (inputs, return value, failure mode) one at a time, along with the pre-written docstrings and TODO steps already in `tools.py`. For `search_listings`, it generated a function that filtered by price and size, then scored by keyword overlap. This matched my spec exactly and I used it with no changes. For `suggest_outfit`, I reviewed the generated prompt template and adjusted the empty-wardrobe branch to explicitly mention the item's style_tags and colors, since the first version was too generic. For `create_fit_card`, I changed the LLM temperature from the AI's default of 0.7 up to 0.95 after testing showed the captions sounded too similar across repeated calls with the same input.

**Instance 2 - Wiring up the planning loop in `agent.py`:**
I gave Claude the Planning Loop, State Management, and Architecture sections from planning.md, plus the pre-written `_new_session()` function and TODO comments already in the starter file. It generated a `run_agent()` function and also proposed a `_parse_query()` helper using the LLM to extract search parameters from the natural language query, since my planning.md hadn't specified a parsing method. I reviewed the generated JSON parsing logic and added a try/except fallback so that if the LLM returns malformed JSON, the agent still works by using the raw query as the description instead of crashing.