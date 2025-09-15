# src/dialog.py
import os, json, re, random
from typing import List, Dict, Any, Optional

USE_LLM = bool(os.getenv("OPENAI_API_KEY"))
DEFAULT_LEVELS = ["basic", "intermediate", "advanced", "scenario"]

SYSTEM_PROMPT = (
    "You are an experienced Excel interviewer. Ask ONE concise question at a time, "
    "adapt difficulty, prefer practical scenarios. Keep < 2 sentences. "
    "Return strict JSON: {id, level, prompt, concepts_required, acceptable_terms, model_answer}."
)

NEXT_Q_SCHEMA = {
    "id": "string-id",
    "level": "basic|intermediate|advanced|scenario",
    "prompt": "question text",
    "concepts_required": ["list", "of", "concepts"],
    "acceptable_terms": ["synonyms"],
    "model_answer": "ideal concise answer"
}

HINT_SCHEMA = {"hint": "1-2 sentence nudge; do not reveal full answer"}

def _safe_json(txt: str) -> Optional[dict]:
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

def _choose_level(prev_scores: List[float]) -> str:
    if not prev_scores: return "basic"
    last = prev_scores[-1]
    if last >= 3.8: return "advanced"
    if last >= 2.8: return "intermediate"
    return "basic"


def _fallback(level: str) -> Dict[str, Any]:
    import random
    return {
        "id": f"FB-{level}-{random.randint(1000,9999)}",
        "level": level,
        "prompt": "When would you use INDEX-MATCH instead of VLOOKUP? Give a short formula.",
        "concepts_required": ["INDEX","MATCH","left lookup","column insertion safety"],
        "acceptable_terms": ["two-way lookup","exact match"],
        "model_answer": "INDEX(Marks, MATCH(ID, IDs, 0)) supports left lookups and is robust to column insertion."
    }


def _slug(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:24] or "q"

def _make_id(prompt: str) -> str:
    return f"LLM-{_slug(prompt)}-{random.randint(100,999)}"

# Fallback prompt pool (ASCII only, no fancy dashes) to ensure variety:
_FALLBACK_POOL = {
    "basic": [
        "Explain absolute vs relative references with an example.",
        "What does the $ symbol do in a formula? Give a short example.",
        "How would you freeze top row and first column? Why is it useful?"
    ],
    "intermediate": [
        "When would you use SUMIFS vs COUNTIFS? Give a short example.",
        "Conditional formatting: highlight duplicates across two columns with a formula.",
        "Create a data validation dropdown that spills UNIQUE values from a table column."
    ],
    "advanced": [
        "When would you use INDEX-MATCH instead of VLOOKUP? Give a short formula.",
        "Explain XLOOKUP advantages over VLOOKUP and show an example.",
        "Use LET and LAMBDA to create a reusable CleanText function (trim+lower+remove spaces)."
    ],
    "scenario": [
        "You get a messy monthly CSV: outline Power Query steps to clean and normalize it.",
        "Dataset Orders(Id, Date, Region, Product, Qty, Price): find top 3 regions by revenue YTD and explain refresh."
    ],
}

def _fallback_alt(level: str, recent_prompts: List[str]) -> Dict[str, Any]:
    recent_set = {p.strip().lower() for p in recent_prompts}
    plist = _FALLBACK_POOL.get(level, _FALLBACK_POOL["basic"])
    # pick first prompt not in recent; otherwise random
    for p in plist:
        if p.strip().lower() not in recent_set:
            prompt = p
            break
    else:
        prompt = random.choice(plist)
    return {
        "id": _make_id(prompt),
        "level": level,
        "prompt": prompt,
        "concepts_required": ["keywords", "core idea", "best practice"],
        "acceptable_terms": ["synonyms", "alternatives"],
        "model_answer": "A concise, correct explanation with a short formula or steps.",
    }

def llm_next_question(
    transcript: List[Dict[str, Any]],
    prev_scores: List[float],
    used_ids: Optional[set] = None,
    recent_prompts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    used_ids = used_ids or set()
    recent_prompts = recent_prompts or []
    recent_set = {p.strip().lower() for p in recent_prompts}

    level = _choose_level(prev_scores)

    if not USE_LLM:
        # deterministic fallback with variety
        return _fallback_alt(level, recent_prompts)

    # Call LLM with explicit avoidance hints
    try:
        from openai import OpenAI
        client = OpenAI()
        user_payload = {
            "transcript": transcript[-8:],
            "suggest_level": level,
            "schema": NEXT_Q_SCHEMA,
            "constraints": {
                "max_sentences": 2,
                "avoid_repetition": True,
                "excel_focus": True
            },
            "avoid_ids": list(used_ids)[-50:],       # recent IDs to avoid
            "avoid_prompts": list(recent_set)        # recent prompt texts to avoid
        }
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user_payload)}
            ],
            temperature=0.4,
            timeout=20
        )
        data = _safe_json(resp.choices[0].message.content) or {}
    except Exception:
        # quota/network/etc. -> deterministic variety
        return _fallback_alt(level, recent_prompts)

    # Ensure fields
    data.setdefault("level", level)
    data.setdefault("prompt", _fallback_alt(level, recent_prompts)["prompt"])
    data.setdefault("concepts_required", ["keywords", "core idea", "best practice"])
    data.setdefault("acceptable_terms", ["synonyms", "alternatives"])
    data.setdefault("model_answer", "A concise, correct explanation with a short formula or steps.")
    data.setdefault("id", _make_id(data.get("prompt", "")))

    # Post-filter de-dup: ID and prompt text
    if data["id"] in used_ids or data.get("prompt", "").strip().lower() in recent_set:
        # Return an alternate deterministic prompt that’s not in recent history
        return _fallback_alt(level, recent_prompts)

    return data
def llm_hint(question: Dict[str, Any], transcript: List[Dict[str, Any]]) -> str:
    if not USE_LLM:
        need = question.get("concepts_required", [])
        return "Consider: " + ", ".join(need[:3]) if need else "Think about the key Excel function(s)."
    try:
        from openai import OpenAI
        client = OpenAI()
        user_payload = {"question": question.get("prompt"),
                        "concepts_required": question.get("concepts_required", []),
                        "schema": HINT_SCHEMA}
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role":"system","content":"Provide a subtle hint, not the answer."},
                      {"role":"user","content":json.dumps(user_payload)}],
            temperature=0.5,
            timeout=15
        )
        data = _safe_json(resp.choices[0].message.content) or {}
        return data.get("hint", "Think about the function parameters you would need.")
    except Exception:
        need = question.get("concepts_required", [])
        return "Consider: " + ", ".join(need[:3]) if need else "Think about the key Excel function(s)."

def fallback_next_question(bank, used_ids, prev_scores):
    level = _choose_level(prev_scores)
    candidates = [q for q in bank if q["id"] not in used_ids and q.get("level")==level]
    if not candidates:
        candidates = [q for q in bank if q["id"] not in used_ids]
    q = candidates[0] if candidates else random.choice(bank)
    q.setdefault("model_answer", "A concise, correct explanation of the concept.")
    return q
