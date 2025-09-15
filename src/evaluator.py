import os, json
from rapidfuzz import fuzz

DIMENSIONS = ["accuracy", "completeness", "clarity", "depth"]

# Weights configurable via .env
W_ACC = float(os.getenv("W_ACC", "0.38"))
W_COMP = float(os.getenv("W_COMP", "0.30"))
W_CLAR = float(os.getenv("W_CLAR", "0.18"))
W_DEPTH = float(os.getenv("W_DEPTH", "0.14"))

# Lower threshold so decent answers don’t look like zeros
KW_HIT_THRESHOLD = int(os.getenv("KW_HIT_THRESHOLD", "68"))

def _norm(v, lo=0, hi=100):
    v = max(lo, min(hi, v))
    return round((v - lo) / (hi - lo) * 5, 2)

def _keyword_hit(ans: str, word: str) -> bool:
    return max(
        fuzz.partial_ratio(ans, word.lower()),
        fuzz.token_set_ratio(ans, word.lower())
    ) >= KW_HIT_THRESHOLD

def keyword_scoring(answer: str, q: dict) -> dict:
    ans = (answer or "").lower().strip()
    need_terms = q.get("concepts_required", [])
    hits = sum(1 for kw in need_terms if _keyword_hit(ans, kw))
    need = max(1, len(need_terms))
    accuracy = _norm((hits / need) * 100)

    extras = q.get("acceptable_terms", [])
    extra_hits = sum(1 for alt in extras if _keyword_hit(ans, alt))
    completeness_raw = min(100, (hits / need * 70) + (min(extra_hits, 3) * 10))
    completeness = _norm(completeness_raw)

    # Clarity: sentences & structure; give a floor if the user wrote something non-empty
    sentences = max(1, len([s for s in ans.replace("!", ".").replace("?", ".").split(".") if s.strip()]))
    clarity = _norm(min(100, sentences * 12))
    if ans:  # floor to avoid 0.0-looking clarity when they wrote something
        clarity = max(clarity, 1.2)

    # Depth: modern Excel usage (lightly)
    modern = ["xlookup", "dynamic array", "filter", "unique", "power query", "lambda", "let", "sumifs", "dax", "power pivot"]
    depth_hits = sum(1 for m in modern if m in ans)
    depth = _norm(min(100, depth_hits * 20))

    total = round(accuracy * W_ACC + completeness * W_COMP + clarity * W_CLAR + depth * W_DEPTH, 2)
    return {"accuracy": accuracy, "completeness": completeness, "clarity": clarity, "depth": depth,
            "total": total, "rationale": "rule-based"}

def llm_scoring(answer: str, q: dict, model: str | None = None) -> dict:
    from openai import OpenAI
    client = OpenAI()
    model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
    sys = (
        "You are a rigorous Excel interviewer. Grade on 0-5 for Accuracy, Completeness, Clarity, Depth. "
        "Keep totals reasonable. Return JSON only with those keys plus optional 'corrections'."
    )
    user = json.dumps({"question": q.get("prompt"), "answer": answer})
    resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": sys},
                                                                 {"role": "user", "content": user}])
    try:
        data = json.loads(resp.choices[0].message.content)
    except Exception:
        data = {"accuracy": 0, "completeness": 0, "clarity": 0, "depth": 0, "total": 0,
                "reasons": "Parse error", "corrections": []}
    for k in DIMENSIONS + ["total"]:
        if k in data:
            data[k] = round(float(data[k]), 2)
    data.setdefault("corrections", [])
    data["rationale"] = "llm"
    return data

def merge_scores(k: dict, l: dict | None) -> dict:
    if not l:
        return k
    # If LLM failed (e.g., total is 0 with reasons/parse error), fall back to keyword-only.
    if l.get("total", 0) == 0 and k.get("total", 0) > 0:
        out = k.copy()
        out["rationale"] = "rule-based (LLM fallback)"
        return out

    out = {}
    for d in DIMENSIONS:
        out[d] = round((k.get(d, 0) + l.get(d, 0)) / 2, 2)
    out["total"] = round((k.get("total", 0) + l.get("total", 0)) / 2, 2)
    out["rationale"] = "hybrid"
    out["corrections"] = l.get("corrections", [])
    return out

