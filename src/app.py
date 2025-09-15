# src/app.py
import os, time, json
import streamlit as st
from dotenv import load_dotenv
from bank import load_questions
from evaluator import keyword_scoring, llm_scoring, merge_scores
from report import render_markdown, render_pdf, render_csv, band_from_score
from dialog import USE_LLM, llm_next_question, llm_hint, fallback_next_question

load_dotenv()
APP_NAME = os.getenv("APP_NAME", "Excel Mock Interviewer")
MAX_Q = int(os.getenv("NUM_QUESTIONS", "7"))

def can_use_llm() -> bool:
    """Runtime check (works with Streamlit Cloud Secrets)."""
    return bool(os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="centered")

# ---------------- Session bootstrap ----------------
if "chat" not in st.session_state:
    st.session_state.chat = []  # [{role:"assistant"/"user", "content": str}]
if "engine" not in st.session_state:
    st.session_state.engine = {
        "started_at": time.time(),
        "q_count": 0,              # number of questions that have been ASKED
        "used_ids": set(),         # track asked question ids to avoid repeats
        "questions_bank": load_questions(),
        "history": [],             # [{q, a, score, time_s}]
        "scores": [],              # per-question total score
        "current_q": None,         # dict for current question
        "q_start": None,           # timestamp when current question was asked
        "awaiting_answer": False,  # True right after asking; False after scoring/skip
        "revealed": set(),         # "review model answer" buttons clicked
        "deterministic_only": os.getenv("DETERMINISTIC_ONLY", "false").lower() == "true",
        "mode_reason": "",
        "show_report": False,      # whether to show the report box
        "report_paths": {},        # stores generated file paths & S snapshot
    }
E = st.session_state.engine

# ---------------- UI helpers ----------------
def render_mode_banner():
    use_llm_active = (not E["deterministic_only"]) and can_use_llm()
    mode = "LLM-driven" if use_llm_active else "Deterministic"
    color = "#0f9960" if use_llm_active else "#e03a3e"
    st.markdown(
        f"""
        <div style="display:flex;gap:8px;align-items:center;">
          <div style="padding:8px 12px;border-radius:9999px;background:{color};color:white;font-weight:600;display:inline-block;">
            {mode}
          </div>
          <div style="opacity:0.7">Ask/score adaptively with {'LLM' if use_llm_active else 'keyword rubric'}.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if E.get("mode_reason") and not use_llm_active:
        st.caption(f"Reason: {E['mode_reason']}")

def show_progress():
    if MAX_Q > 0:
        st.progress(min(E["q_count"], MAX_Q) / MAX_Q, text=f"Question {min(E['q_count'], MAX_Q)} of {MAX_Q}")

# ---------------- Sidebar (safe toggle + timer) ----------------
with st.sidebar:
    st.header("Settings")
    default_toggle = can_use_llm() and (not E["deterministic_only"])
    use_llm_requested = st.toggle("Use LLM (if available)", value=default_toggle, disabled=not can_use_llm())
    new_det_only = not (use_llm_requested and can_use_llm())

    if new_det_only != E["deterministic_only"]):
        # switch modes without crashing; clear reason when enabling LLM
        E["deterministic_only"] = new_det_only
        E["mode_reason"] = "" if not new_det_only else E.get("mode_reason", "")
        st.toast("Mode changed: " + ("Deterministic" if new_det_only else "LLM-driven"), icon="🔁")
        st.rerun()

    # Per-question timer display (updates on each rerun)
    if E.get("q_start"):
        elapsed = int(time.time() - E["q_start"])
        st.metric("Time on current question (s)", elapsed)

    if st.button("Restart Interview"):
        st.session_state.clear()
        st.rerun()

# ---------------- Core actions ----------------
def append_assistant(msg: str):
    st.session_state.chat.append({"role": "assistant", "content": msg})

def append_user(msg: str):
    st.session_state.chat.append({"role": "user", "content": msg})

def ask_next_question():
    """
    Ask another question only if we're not already waiting for an answer.
    Starts timer, marks awaiting_answer=True, increments q_count.
    Safe LLM->deterministic fallback with reason & toast.
    """
    if E["awaiting_answer"]:
        return  # prevent double-ask on rerun

    try:
        if (not E["deterministic_only"]) and can_use_llm():
            q = llm_next_question(st.session_state.chat, E["scores"])
        else:
            q = fallback_next_question(E["questions_bank"], E["used_ids"], E["scores"])
    except Exception as e:
        # Auto-switch to deterministic mode on any LLM error
        E["deterministic_only"] = True
        E["mode_reason"] = f"LLM unavailable: {e.__class__.__name__}"
        st.toast("Switched to deterministic mode (LLM unavailable).", icon="⚠️")
        q = fallback_next_question(E["questions_bank"], E["used_ids"], E["scores"])

    # Ensure we don't repeat a previously asked id
    qid = q.get("id", f"Q-{E['q_count']+1}")
    if qid in E["used_ids"]:
        # pick another deterministic question if collision occurs
        q = fallback_next_question(E["questions_bank"], E["used_ids"], E["scores"])
        qid = q.get("id", f"Q-{E['q_count']+1}")

    E["current_q"] = q
    E["used_ids"].add(qid)
    E["q_start"] = time.time()   # <-- start timer here
    E["awaiting_answer"] = True
    E["q_count"] += 1

    append_assistant(q["prompt"])

# ---------------- First render ----------------
st.title("📊 " + APP_NAME)
render_mode_banner()
show_progress()
st.markdown("> Answer in a few sentences or formulas. Type **hint** for a nudge, **skip** to move on.")

if not st.session_state.chat:
    append_assistant(
        "Hi! I’ll run your Excel mock interview. I’ll ask one question at a time. "
        "Say **hint** if you’d like a nudge, or **skip** to move on."
    )
    ask_next_question()

# ---------------- Replay chat so far ----------------
for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------- Chat input ----------------
prompt = st.chat_input("Type your answer here… (or 'hint' / 'skip')")
if prompt is not None:
    text = prompt.strip()
    if text:
        append_user(text)

        # Guard: we should be awaiting an answer before processing it
        if not E["awaiting_answer"]:
            # If user typed while not awaiting (e.g., double submit), just ignore gracefully
            st.toast("Hold on — I’ll ask the next question first.", icon="⏳")
            st.rerun()

        # Commands: hint / skip
        if text.lower() == "hint":
            q = E["current_q"]
            if q:
                try:
                    if (not E["deterministic_only"]) and can_use_llm():
                        h = llm_hint(q, st.session_state.chat)
                    else:
                        need = q.get("concepts_required", [])
                        h = "Consider: " + ", ".join(need[:3]) if need else "Think about the key Excel function(s)."
                except Exception:
                    need = q.get("concepts_required", [])
                    h = "Consider: " + ", ".join(need[:3]) if need else "Think about the key Excel function(s)."
                append_assistant(f"Hint: {h}")
            st.rerun()

        if text.lower() == "skip":
            q = E["current_q"]
            t_s = int(time.time() - (E["q_start"] or time.time()))
            score = keyword_scoring("", q)  # minimal baseline
            E["scores"].append(score.get("total", 0.0))
            E["history"].append({"q": q, "a": "", "score": score, "time_s": t_s})
            E["awaiting_answer"] = False     # <-- allow next question
            append_assistant("Skipped. I’ll move on.")
            if E["q_count"] >= MAX_Q:
                st.rerun()
            ask_next_question()
            st.rerun()

        # Normal answer -> score
        q = E["current_q"]
        t_s = int(time.time() - (E["q_start"] or time.time()))
        k = keyword_scoring(text, q)
        l = None
        if (not E["deterministic_only"]) and can_use_llm():
            try:
                l = llm_scoring(text, q)
            except Exception as e:
                # Switch scoring to deterministic if LLM fails
                E["deterministic_only"] = True
                E["mode_reason"] = f"LLM scoring error: {e.__class__.__name__}"
                st.toast("LLM scoring unavailable; continuing in deterministic mode.", icon="⚠️")
        score = merge_scores(k, l)

        E["scores"].append(score.get("total", 0.0))
        E["history"].append({"q": q, "a": text, "score": score, "time_s": t_s})
        E["awaiting_answer"] = False    # <-- free to ask next

        # Feedback bubble with inline actions
        feedback = (
            f"**Feedback**  \n"
            f"- Accuracy: {score['accuracy']}  \n"
            f"- Completeness: {score['completeness']}  \n"
            f"- Clarity: {score['clarity']}  \n"
            f"- Depth: {score['depth']}  \n"
            f"**Total:** {score['total']} / 5  \n"
            f"_Time taken: {t_s} sec_"
        )
        with st.chat_message("assistant"):
            st.markdown(feedback)
            colA, colB = st.columns(2)
            with colA:
                key_review = f"review_{E['q_count']}_{q.get('id','')}"
                if key_review not in E["revealed"] and st.button("🔍 Review model answer", key=key_review):
                    st.info(q.get("model_answer", "No model answer available."))
                    E["revealed"].add(key_review)
            with colB:
                if st.button("⏭ Next"):
                    if E["q_count"] >= MAX_Q:
                        overall = sum(E["scores"]) / max(1, len(E["scores"]))
                        band = band_from_score(overall)
                        append_assistant(
                            f"That’s the end. Overall score: **{overall:.2f}/5** → **{band}**. Generating your report…"
                        )
                    else:
                        ask_next_question()
                    st.rerun()

        # If user didn’t click "Next", auto-advance unless finished
        if E["q_count"] < MAX_Q:
            ask_next_question()
        else:
            overall = sum(E["scores"]) / max(1, len(E["scores"]))
            band = band_from_score(overall)
            append_assistant(
                f"That’s the end. Overall score: **{overall:.2f}/5** → **{band}**. Generating your report…"
            )
        st.rerun()

# ---------------- Final report (button-revealed) ----------------
if E["q_count"] >= MAX_Q and not E["awaiting_answer"]:
    st.divider()
    st.subheader("✅ Interview Complete")

    if not E.get("show_report"):
        # Only show the button first
        if st.button("📄 Show Report"):
            # Build a snapshot S for rendering & export
            S = {
                "answers": [h["a"] for h in E["history"]],
                "scores": [h["score"] for h in E["history"]],
                "questions": [h["q"] for h in E["history"]],
                "time_s_list": [h.get("time_s") for h in E["history"]],
            }

            # Generate files just-in-time
            os.makedirs("reports", exist_ok=True)
            pdf_path = render_pdf(S, f"reports/report_{int(time.time())}.pdf")
            csv_path = render_csv(S, f"reports/transcript_{int(time.time())}.csv")

            # Store for later use
            E["report_paths"] = {"pdf": pdf_path, "csv": csv_path, "S": S}
            E["show_report"] = True
            st.rerun()
    else:
        # Show the report box with tabs (no nested expanders)
        with st.container(border=True):
            st.markdown("### 📄 Report")

            import pandas as pd
            S_snap = E["report_paths"]["S"]
            rows = []
            for i, s in enumerate(S_snap["scores"], start=1):
                rows.append({
                    "Q": i,
                    "Total": s.get("total", 0.0),
                    "Accuracy": s.get("accuracy", 0.0),
                    "Completeness": s.get("completeness", 0.0),
                    "Clarity": s.get("clarity", 0.0),
                    "Depth": s.get("depth", 0.0),
                })
            df = pd.DataFrame(rows).set_index("Q")

            tab_sum, tab_charts, tab_dl = st.tabs(["Summary", "Charts", "Downloads"])

            # Summary tab
            with tab_sum:
                md = render_markdown(S_snap)
                st.markdown(md)

            # Charts tab
            with tab_charts:
                st.markdown("#### 📈 Score trend (Total)")
                st.line_chart(df[["Total"]])
                show_dims = st.checkbox("Show dimension breakdown", value=False)
                if show_dims:
                    st.line_chart(df[["Accuracy", "Completeness", "Clarity", "Depth"]])

            # Downloads tab
            with tab_dl:
                col1, col2 = st.columns(2)
                with col1:
                    with open(E["report_paths"]["pdf"], "rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            data=f.read(),
                            file_name=os.path.basename(E["report_paths"]["pdf"]),
                            mime="application/pdf",
                        )
                with col2:
                    with open(E["report_paths"]["csv"], "rb") as f:
                        st.download_button(
                            "⬇️ Download CSV",
                            data=f.read(),
                            file_name=os.path.basename(E["report_paths"]["csv"]),
                            mime="text/csv",
                        )

        st.caption("You can close the box or start another interview anytime.")
        if st.button("🔁 Start another interview"):
            st.session_state.clear()
            st.rerun()
