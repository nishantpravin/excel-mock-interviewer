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


def llm_next_question(
    transcript: List[Dict[str, Any]],
    prev_scores: List[float],
    used_ids: Optional[set] = None,
    recent_prompts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate the next question via LLM but avoid repeats:
    - Pass 'avoid_ids' and 'avoid_prompts' to the model
    - If the model still returns a duplicate id/prompt, regenerate a fresh id
    """
    used_ids = used_ids or set()
    recent_prompts = recent_prompts or []

    from openai import OpenAI
    client = OpenAI()
    level = _choose_level(prev_scores)

    user_payload = {
        "transcript": transcript[-8:],
        "suggest_level": level,
        "schema": NEXT_Q_SCHEMA,
        "constraints": {"max_sentences": 2, "avoid_repetition": True, "excel_focus": True},
        "avoid_ids": list(used_ids)[-50:],            # pass a bounded list
        "avoid_prompts": recent_prompts[-10:],        # last few prompts
    }

    try:
        resp = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":json.dumps(user_payload)}
            ],
            temperature=0.4,
            timeout=20,
        )
        data = _safe_json(resp.choices[0].message.content) or {}
    except Exception:
        # fallback already in your file:
        return _fallback(level)

    # ensure required fields + generate id if missing
    data.setdefault("level", level)
    data.setdefault("prompt", _fallback(level)["prompt"])
    data.setdefault("concepts_required", _fallback(level)["concepts_required"])
    data.setdefault("acceptable_terms", _fallback(level)["acceptable_terms"])
    data.setdefault("model_answer", _fallback(level)["model_answer"])
    data.setdefault("id", _make_id(data.get("prompt", "")))

    # de-dup id/prompt locally (last line of defense)
    if data["id"] in used_ids:
        data["id"] = _make_id(data["prompt"])
    if data.get("prompt", "").strip() in {p.strip() for p in recent_prompts}:
        # If prompt text repeats, keep prompt but force a fresh id
        data["id"] = _make_id(data["prompt"])

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
