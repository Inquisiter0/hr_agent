# app.py
import os
from dotenv import load_dotenv
import streamlit as st
from agents.jd_parser import parse_jd
from agents.profile_agent import parse_resume, parse_linkedin_json
from agents.score_agent import score_candidate
from agents.report_agent import generate_html_report
from utils.override_log import log_override

load_dotenv()

st.set_page_config(page_title="HR Shortlisting Agent", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }
.stApp { background: #0f0f13; color: #e8e4dd; }
.hero {
    background: linear-gradient(135deg, #1a1a24, #12121a);
    border: 1px solid #2a2a3a; border-radius: 16px;
    padding: 2.5rem 2rem; margin-bottom: 2rem; text-align: center;
}
.hero h1 {
    font-size: 2.6rem;
    background: linear-gradient(90deg, #f5c842, #f0956a);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;
}
.hero p { color: #7a7a8a; margin-top: 0.4rem; }
.sec { font-size: 1rem; font-weight: 600; color: #f5c842;
    border-bottom: 1px solid #2a2a3a; padding-bottom: 0.4rem; margin-bottom: 1rem; }
.badge-hire   { background:#1a3a28; color:#4caf7d; border-radius:20px; padding:2px 12px; font-size:0.78rem; font-weight:600; }
.badge-nohire { background:#3a1a1a; color:#e05c5c; border-radius:20px; padding:2px 12px; font-size:0.78rem; font-weight:600; }
.bar-bg   { background:#2a2a3a; border-radius:4px; height:8px; margin-top:2px; }
.bar-fill { height:8px; border-radius:4px; }
.dim-label { font-size:0.78rem; color:#7a7a8a; }
.just { font-size:0.75rem; color:#5a5a6a; margin-top:2px; }
.stButton>button {
    background: linear-gradient(135deg,#f5c842,#f0956a) !important;
    color:#0f0f13 !important; font-weight:600 !important;
    border:none !important; border-radius:8px !important;
}
.stTextArea textarea { background:#16161f !important; color:#e8e4dd !important; border:1px solid #2a2a3a !important; }
div[data-testid="stSidebar"] { background:#0c0c12 !important; border-right:1px solid #1e1e2e; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>HR Shortlisting Agent</h1>
  <p>Llama 3.3 & 3.1 via Groq &nbsp;|&nbsp; 5-Dimension Rubric Scoring &nbsp;|&nbsp; Human-in-the-Loop</p>
</div>
""", unsafe_allow_html=True)

# session state init
for k, v in [("results", []), ("jd_parsed", None), ("overrides", {})]:
    if k not in st.session_state:
        st.session_state[k] = v

# sidebar
with st.sidebar:
    st.markdown("### Configuration")
    model_name = st.selectbox("Model", ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"])
    st.markdown("---")
    st.markdown("**Agent Flow**")
    st.markdown("1. Parse Job Description\n2. Ingest resumes + LinkedIn JSON\n3. Score (5 dimensions)\n4. Rank + HTML report\n5. HR override")
    st.markdown("---")
    st.caption("Powered by Groq.")

tab1, tab2, tab3 = st.tabs(["Input & Run", "Results & Override", "Report"])

# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="sec">Job Description</div>', unsafe_allow_html=True)
        jd_text = st.text_area(
            "jd", height=340,
            placeholder="Paste the full Job Description here...",
            label_visibility="collapsed"
        )

    with col2:
        st.markdown('<div class="sec">Candidate Files</div>', unsafe_allow_html=True)

        uploaded_resumes = st.file_uploader(
            "Resumes (PDF or DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=True
        )

        st.markdown("**LinkedIn JSON**")
        st.caption(
            "Go to LinkedIn Settings > Data Privacy > Get a copy of your data > "
            "select Profile data > Request archive. Upload the Profile.json file here."
        )
        uploaded_linkedin = st.file_uploader(
            "LinkedIn JSON files",
            type=["json"],
            accept_multiple_files=True
        )

    st.markdown("---")
    run_col, status_col = st.columns([1, 3])
    with run_col:
        run_btn = st.button("Run Agent", use_container_width=True)

    if run_btn:
        if not jd_text.strip():
            st.error("Paste a Job Description first.")
        elif not uploaded_resumes and not uploaded_linkedin:
            st.error("Upload at least one resume or LinkedIn JSON file.")
        else:
            with status_col:
                bar = st.progress(0, text="Starting...")

            results = []

            bar.progress(10, text="Parsing Job Description...")
            try:
                jd_parsed = parse_jd(jd_text, model=model_name)
                st.session_state.jd_parsed = jd_parsed
            except Exception as e:
                st.error(f"JD parsing failed: {e}")
                st.stop()

            total_files = len(uploaded_resumes or []) + len(uploaded_linkedin or [])
            done = 0

            for f in (uploaded_resumes or []):
                pct = 10 + int(80 * done / max(total_files, 1))
                bar.progress(pct, text=f"Parsing resume: {f.name}")
                try:
                    profile = parse_resume(f)
                    scored  = score_candidate(profile, jd_parsed, model=model_name)
                    scored["name"]   = profile.get("name", f.name)
                    scored["source"] = f.name
                    results.append(scored)
                except Exception as e:
                    st.warning(f"Failed: {f.name} — {e}")
                done += 1

            for f in (uploaded_linkedin or []):
                pct = 10 + int(80 * done / max(total_files, 1))
                bar.progress(pct, text=f"Parsing LinkedIn: {f.name}")
                try:
                    profile = parse_linkedin_json(f)
                    scored  = score_candidate(profile, jd_parsed, model=model_name)
                    scored["name"]   = profile.get("name", f.name)
                    scored["source"] = f.name
                    results.append(scored)
                except Exception as e:
                    st.warning(f"Failed: {f.name} — {e}")
                done += 1

            results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
            st.session_state.results = results
            bar.progress(100, text="Done. Switch to Results tab.")
            st.success(f"Processed {len(results)} candidate(s).")

# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    if not st.session_state.results:
        st.info("No results yet. Run the agent in the Input tab.")
    else:
        st.markdown(
            f'<div class="sec">Ranked Shortlist — {len(st.session_state.results)} candidate(s)</div>',
            unsafe_allow_html=True
        )

        dims_cfg = [
            ("skills_match",          "Skills Match",          30),
            ("experience_relevance",  "Experience Relevance",  25),
            ("education_certs",       "Education & Certs",     15),
            ("project_portfolio",     "Project / Portfolio",   20),
            ("communication_quality", "Communication Quality", 10),
        ]

        for idx, cand in enumerate(st.session_state.results):
            name    = cand.get("name", f"Candidate {idx+1}")
            total   = cand.get("total_score", 0)
            rec     = cand.get("recommendation", "No Hire")
            dims    = cand.get("dimensions", {})
            is_hire = "hire" in rec.lower() and "no" not in rec.lower()
            tc      = "#4caf7d" if total >= 7 else "#f5c842" if total >= 5 else "#e05c5c"
            badge   = '<span class="badge-hire">Hire</span>' if is_hire else '<span class="badge-nohire">No Hire</span>'

            with st.expander(f"#{idx+1}  {name}  |  {total:.1f}/10  |  {rec}", expanded=(idx == 0)):
                c1, c2 = st.columns([3, 2])

                with c1:
                    st.markdown("**Dimension Scores**")
                    for key, label, weight in dims_cfg:
                        d  = dims.get(key, {})
                        s  = d.get("score", 0)
                        j  = d.get("justification", "")
                        sc = "#4caf7d" if s >= 7 else "#f5c842" if s >= 5 else "#e05c5c"
                        st.markdown(f"""
                        <div style="margin:6px 0">
                          <div class="dim-label">{label} ({weight}%) — {s}/10</div>
                          <div class="bar-bg"><div class="bar-fill" style="width:{s*10}%;background:{sc}"></div></div>
                          <div class="just">{j}</div>
                        </div>""", unsafe_allow_html=True)

                with c2:
                    st.markdown("**Summary**")
                    st.markdown(f"Total: **{total:.1f} / 10**")
                    st.markdown(f"Recommendation: {badge}", unsafe_allow_html=True)
                    st.markdown(f"Source: `{cand.get('source', '')}`")
                    if cand.get("overridden"):
                        st.info(f"Override: {cand.get('override_reason', '')}")

                    st.markdown("---")
                    st.markdown("**HR Override**")
                    new_score = st.number_input(
                        "Override score (0-10)", 0.0, 10.0,
                        float(total), 0.5, key=f"sc_{idx}"
                    )
                    reason = st.text_input(
                        "Reason", key=f"rs_{idx}",
                        placeholder="e.g. Strong interview performance"
                    )
                    if st.button("Apply Override", key=f"btn_{idx}"):
                        if reason.strip():
                            st.session_state.results[idx]["total_score"]     = new_score
                            st.session_state.results[idx]["overridden"]      = True
                            st.session_state.results[idx]["override_reason"] = reason
                            st.session_state.overrides[name] = {
                                "original": total, "new": new_score, "reason": reason
                            }
                            log_override(name, total, new_score, reason)
                            st.success("Override logged.")
                        else:
                            st.warning("Enter a reason before applying.")

        if st.session_state.overrides:
            st.markdown("---")
            st.markdown("**Override Audit Log**")
            st.json(st.session_state.overrides)

# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    if not st.session_state.results:
        st.info("No results yet. Run the agent first.")
    else:
        if st.button("Generate HTML Report"):
            with st.spinner("Generating..."):
                path = generate_html_report(
                    st.session_state.results,
                    st.session_state.jd_parsed or {},
                    output_dir="output"
                )
            with open(path, "r", encoding="utf-8") as f:
                html_bytes = f.read().encode()
            st.download_button("Download Report", html_bytes, "shortlist_report.html", "text/html")
            st.success("Report ready.")