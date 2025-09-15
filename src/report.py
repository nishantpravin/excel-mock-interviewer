# src/report.py
from fpdf import FPDF
import re, textwrap, csv

# ---------- Sanitizer (ASCII-safe, catches U+2011 etc.) ----------
REPLACEMENTS = {
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u2212": "-", "\u00ad": "-", "…": "...", "“": '"', "”": '"', "’": "'",
    "\u00a0": " ", "\u2009": " ", "\u202f": " ",
}
def sanitize(txt: str) -> str:
    if not txt:
        return ""
    s = re.sub("|".join(map(re.escape, REPLACEMENTS.keys())),
               lambda m: REPLACEMENTS[m.group(0)], txt)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def wrap(s: str, width_chars: int = 110) -> str:
    return "\n".join(
        textwrap.fill(line, width=width_chars, break_long_words=True, break_on_hyphens=True)
        for line in s.splitlines()
    )

# ---------- Banding ----------
def band_from_score(overall: float):
    if overall >= 3.5:
        return "PASS"
    if overall >= 2.0:
        return "BORDERLINE"
    return "FAIL"

# ---------- Markdown summary ----------
def render_markdown(S: dict) -> str:
    lines = ["# Excel Mock Interview - Summary\n"]
    overall = sum(s.get("total", 0) for s in S["scores"]) / max(1, len(S["scores"]))
    band = band_from_score(overall)
    lines.append(f"**Overall Score:** {overall:.2f} / 5.00  \n")
    lines.append(f"**Decision:** {band}\n")
    for i, (q, s) in enumerate(zip(S["questions"], S["scores"])):
        lines.append(f"\n### Q{i+1}. {sanitize(q['prompt'])}")
        lines.append(f"- Scores: Acc {s['accuracy']}, Comp {s['completeness']}, "
                     f"Clar {s['clarity']}, Depth {s['depth']} (Total {s['total']})")
        if s.get("corrections"):
            lines.append("- Improvements: " + "; ".join(map(sanitize, s["corrections"])))
    return "\n".join(lines)

# ---------- PDF summary ----------
def render_pdf(S: dict, path: str) -> str:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    epw = pdf.w - 2 * pdf.l_margin

    pdf.set_font("Arial", "B", 14)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(epw, 8, sanitize("Excel Mock Interview - Summary"))

    overall = sum(s.get("total", 0) for s in S["scores"]) / max(1, len(S["scores"]))
    band = band_from_score(overall)

    pdf.set_font("Arial", size=11)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(epw, 6, sanitize(f"Overall Score: {overall:.2f} / 5.00"))
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(epw, 6, sanitize(f"Decision: {band}"))

    for i, (q, s) in enumerate(zip(S["questions"], S["scores"])):
        pdf.ln(1)
        pdf.set_font("Arial", "B", 11)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 6, sanitize(f"Q{i+1}. {q['prompt']}"))

        pdf.set_font("Arial", size=10)
        scores_line = (f"Scores: Acc {s['accuracy']} | Comp {s['completeness']} | "
                       f"Clar {s['clarity']} | Depth {s['depth']} | Total {s['total']}")
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 5, wrap(sanitize(scores_line), width_chars=120))

        corrections = s.get("corrections") or []
        if corrections:
            corr_text = "Improvements: " + "; ".join(map(sanitize, corrections))
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(epw, 5, wrap(corr_text, width_chars=120))

    pdf.output(path)
    return path

# ---------- CSV export ----------
def render_csv(S: dict, path: str) -> str:
    # S may not include time_s (only app has it); try to fetch if present
    # When called from app, we'll pass a synthetic S built from history if needed.
    rows = [("q_index","question","answer","accuracy","completeness","clarity","depth","total","time_s")]
    # Support both: S directly from app history OR earlier structure
    time_list = S.get("time_s_list", [None]*len(S.get("scores", [])))
    for i, (q, a, s, t) in enumerate(zip(
        S.get("questions", []),
        S.get("answers", []),
        S.get("scores", []),
        time_list
    )):
        rows.append((
            i+1,
            sanitize(q.get("prompt","")),
            sanitize(a),
            s.get("accuracy",0),
            s.get("completeness",0),
            s.get("clarity",0),
            s.get("depth",0),
            s.get("total",0),
            t if t is not None else ""
        ))
    with open(path, "w", newline="", encoding="utf-8") as f:
        import csv
        csv.writer(f).writerows(rows)
    return path
