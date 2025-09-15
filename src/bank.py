# src/bank.py
import json, os, re

REPLACEMENTS = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2212": "-", "\u00ad": "-", "…": "...", "“": '"', "”": '"', "’": "'",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ",
}
def _sanitize(s: str) -> str:
    if not isinstance(s, str): return s
    s = re.sub("|".join(map(re.escape, REPLACEMENTS.keys())), lambda m: REPLACEMENTS[m.group(0)], s)
    return " ".join(s.split())

def load_questions():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for q in data.get("questions", []):
        q["prompt"] = _sanitize(q.get("prompt", ""))
        q["model_answer"] = _sanitize(q.get("model_answer", ""))
        for k in ("concepts_required", "acceptable_terms", "must_not"):
            if k in q and isinstance(q[k], list):
                q[k] = [_sanitize(x) for x in q[k]]
    return data["questions"]
