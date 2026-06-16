# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset and returns items that match the user's description, size, and price constraints. It filters listings by keyword matching against the title, description, and style_tags fields, then applies size and price filters if provided.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A plain-language description of the item the user is looking for (e.g. "vintage graphic tee"). Used to match against listing titles, descriptions, and style_tags.
- `size` (str): The user's size (e.g. "M", "W30 L30"). If None, size filtering is skipped.
- `max_price` (float): The maximum price the user is willing to pay. If None, price filtering is skipped.

**What it returns:**
A list of matching listing dictionaries, each containing: id (str), title (str), description (str), category (str), style_tags (list[str]), size (str), condition (str), price (float), colors (list[str]), brand (str or None), platform (str). Returns an empty list if no matches are found. Results are sorted by price ascending.

**What happens if it fails or returns nothing:**
If the returned list is empty, the agent sets an error message in the session: "No listings found matching your search. Try broadening your description, adjusting your size, or raising your max price." The agent stops and does not call suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Given a specific thrifted item and the user's current wardrobe, uses the LLM to suggest one or more complete outfit combinations. It formats the new item and wardrobe contents into a prompt and returns a natural-language outfit suggestion.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The selected listing dict returned by search_listings. Contains title, description, category, colors, style_tags, condition, price, and platform.
- `wardrobe` (dict): The user's wardrobe in the standard schema format, a dict with an 'items' key containing a list of wardrobe item dicts. Each wardrobe item has: id, name, category, colors, style_tags, and optional notes.

**What it returns:**
A string containing a natural-language outfit suggestion, which wardrobe pieces to pair with the new item, how to style them, and why the combination works. If the wardrobe is empty, returns general styling advice for the new item based on its style_tags and colors alone.

**What happens if it fails or returns nothing:**
If wardrobe['items'] is empty, the agent does not crash, instead suggest_outfit generates general styling advice using only the new item's attributes. If the LLM call fails, the tool returns the string: "Could not generate an outfit suggestion. Please try again."

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable caption for a complete outfit, the kind of text someone would use for an Instagram or TikTok post. Uses the LLM with a creative prompt to produce varied, natural-sounding output each time.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by suggest_outfit.
- `new_item` (dict): The selected listing dict, used to include specific details like the item title, price, and platform in the caption.

**What it returns:**
A short string (2–4 sentences) written in a casual, social-media-friendly tone. Includes the thrifted item, price, and platform. Output varies each time even for the same input due to LLM temperature settings.

**What happens if it fails or returns nothing:**
If outfit is an empty string or None, the tool returns the error string: "Could not generate a fit card because outfit description was missing." If the LLM call fails, returns: "Could not generate a fit card. Please try again."

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The planning loop runs sequentially with conditional branching based on the result of each tool call:

1. Call `search_listings(description, size, max_price)` with the user's inputs.
2. Check if results is an empty list.
   - If YES: set `session["error"]` to the no-results message and return the session immediately. Do NOT call suggest_outfit or create_fit_card.
   - If NO: set `session["selected_item"] = results[0]` (the top result) and continue.
3. Call `suggest_outfit(session["selected_item"], wardrobe)`.
   - Set `session["outfit_suggestion"]` to the returned string.
   - If the string starts with "Could not generate", set `session["error"]` and return early.
4. Call `create_fit_card(session["outfit_suggestion"], session["selected_item"])`.
   - Set `session["fit_card"]` to the returned string.
5. Return the completed session.

The agent never calls suggest_outfit or create_fit_card if search_listings returns no results. The agent never calls create_fit_card if suggest_outfit fails.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
All state is stored in a single session dictionary that is initialized at the start of each interaction and passed through each step of the planning loop. The session dict has the following keys:

- `session["query"]` - the original user query string, set at the start
- `session["selected_item"]` - the top listing dict returned by search_listings, set after step 1
- `session["outfit_suggestion"]` - the outfit suggestion string returned by suggest_outfit, set after step 2
- `session["fit_card"]` - the fit card caption string returned by create_fit_card, set after step 3
- `session["error"]` - an error message string, set if any tool fails; None if no error

Each tool receives its inputs directly from the session dict rather than from the user. The user only provides input once - at the start - and the agent handles everything from there.


---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] = "No listings found matching your search. Try broadening your description, adjusting your size, or raising your max price." Returns session immediately without calling further tools. |
| suggest_outfit | Wardrobe is empty | Generates general styling advice using only the new item's attributes (colors, style_tags, category) instead of crashing. Returns a useful string rather than an error. |
| create_fit_card | Outfit input is missing or empty string | Returns the error string "Could not generate a fit card because outfit description was missing." without calling the LLM. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

     User Input (description, size, max_price, wardrobe)

│

▼

┌─────────────────────────────────────────────────────┐

│                   Planning Loop                     │

│                                                     │

│  1. search_listings(description, size, max_price)   │

│          │                                          │

│          ├── results == [] ──► session["error"]     │

│          │                         │                │

│          │                         ▼                │

│          │                      RETURN EARLY        │

│          │                                          │

│          └── results != [] ──► session["selected_item"] = results[0]

│                                    │                │

│  2. suggest_outfit(selected_item, wardrobe)         │

│          │                                          │

│          ├── LLM fails ──► session["error"]         │

│          │                      │                   │

│          │                      ▼                   │

│          │                  RETURN EARLY            │

│          │                                          │

│          └── success ──► session["outfit_suggestion"]

│                                    │                │

│  3. create_fit_card(outfit_suggestion, selected_item)

│          │                                          │

│          └── success ──► session["fit_card"]        │

│                                    │                │

└────────────────────────────────────┼────────────────┘

│

▼

Return session to UI

(selected_item, outfit_suggestion, fit_card)


---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I will give Claude the Tool 1 spec block (inputs, return value, failure mode) and ask it to implement `search_listings()` in `tools.py` using `load_listings()` from the data loader. I will verify the output by checking that it filters by all three parameters, handles None values for size and max_price, and returns an empty list (not an exception) when nothing matches. I will test with 3 queries: one that returns results, one with an impossible price, and one with a size that doesn't exist.

For Tool 2, I will give Claude the Tool 2 spec block and ask it to implement `suggest_outfit()` using the Groq API with llama-3.3-70b-versatile. I will verify the output handles the empty wardrobe case and returns a useful string rather than crashing.

For Tool 3, I will give Claude the Tool 3 spec block and ask it to implement `create_fit_card()` using the Groq API with a higher temperature setting (0.9+) for variety. I will verify by running it 3 times on the same input and confirming the outputs differ.

**Milestone 4 — Planning loop and state management:**
I will give Claude the Planning Loop section, State Management section, and Architecture diagram from this file and ask it to implement `run_agent()` in `agent.py`. I will verify the generated code branches on the search_listings result (does not call all three tools unconditionally), stores values in the session dict between steps, and returns early with session["error"] set when search returns nothing.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`. It searches listings by matching "vintage" and "graphic tee" against titles, descriptions, and style_tags, and filters to items priced at or below $30. It returns a list of matching listings sorted by price. The agent sets `session["selected_item"] = results[0]` - the top result, e.g. the Y2K Baby Tee at $18.

**Step 2:**
The agent calls `suggest_outfit(new_item=session["selected_item"], wardrobe=get_example_wardrobe())`. The LLM receives the new item's details (Y2K Baby Tee, white/pink/purple, y2k/vintage style tags) alongside the user's wardrobe items (baggy dark wash jeans, chunky white sneakers, black combat boots, etc.) and returns a natural-language outfit suggestion such as: "Pair this Y2K butterfly tee with your baggy dark wash jeans and chunky white sneakers for a classic early-2000s look. Add your black crossbody bag and keep the rest minimal." The agent sets `session["outfit_suggestion"]` to this string.

**Step 3:**
The agent calls `create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`. The LLM generates a short, casual caption referencing the specific item, price, and platform. For example: "thrifted this y2k butterfly tee off depop for $18 and it was literally made for my baggy jeans era full look incoming". The agent sets `session["fit_card"]` to this string.

**Final output to user:**
The Gradio interface displays three panels:
- **Top Result:** Y2K Baby Tee — Butterfly Print | $18 | depop | excellent condition
- **Outfit Suggestion:** "Pair this Y2K butterfly tee with your baggy dark wash jeans and chunky white sneakers..."
- **Fit Card:** "thrifted this y2k butterfly tee off depop for $18 and it was literally made for my baggy jeans era"
