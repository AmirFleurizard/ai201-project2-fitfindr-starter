"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
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


# ── query parsing ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Use the LLM to extract description, size, and max_price from a natural
    language query. Falls back to using the full query as the description
    if parsing fails.

    Returns:
        dict with keys: description (str), size (str or None), max_price (float or None)
    """
    api_key = os.environ.get("GROQ_API_KEY")
    client = Groq(api_key=api_key)

    prompt = f"""Extract search parameters from this user query about thrifted clothing.

Query: "{query}"

Return ONLY a JSON object with these exact keys:
- "description": a short string describing the item being searched for (keep relevant keywords, remove price/size info)
- "size": the size mentioned, as a string, or null if no size is mentioned
- "max_price": the maximum price mentioned, as a number, or null if no price is mentioned

Example output: {{"description": "vintage graphic tee", "size": "M", "max_price": 30}}

Return ONLY the JSON object, nothing else."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=150,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return {
            "description": parsed.get("description", query),
            "size": parsed.get("size"),
            "max_price": parsed.get("max_price"),
        }
    except Exception:
        # Fallback: use the full query as description, no size/price filter
        return {"description": query, "size": None, "max_price": None}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query into structured parameters
    session["parsed"] = _parse_query(query)

    # Step 3: Call search_listings with parsed parameters
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )

    # Branch: no results found -> set error and return early
    if not session["search_results"]:
        session["error"] = (
            "No listings found matching your search. Try broadening your "
            "description, adjusting your size, or raising your max price."
        )
        return session

    # Step 4: Select the top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: Call suggest_outfit with the selected item and wardrobe
    outfit_suggestion = suggest_outfit(session["selected_item"], session["wardrobe"])
    session["outfit_suggestion"] = outfit_suggestion

    # Branch: suggest_outfit failed -> set error and return early
    if outfit_suggestion.startswith("Could not generate"):
        session["error"] = outfit_suggestion
        return session

    # Step 6: Call create_fit_card with the outfit suggestion and selected item
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])

    # Step 7: Return the completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed query: {session['parsed']}")
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")