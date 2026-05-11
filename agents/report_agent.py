# report_agent.py
import os
from datetime import datetime

DIMS = {
    "skills_match":          ("Skills Match",          30),
    "experience_relevance":  ("Experience Relevance",  25),
    "education_certs":       ("Education & Certs",     15),
    "project_portfolio":     ("Project / Portfolio",   20),
    "communication_quality": ("Communication Quality", 10),
}


def generate_html_report(results: list, jd_parsed: dict, output_dir: str = "output") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{output_dir}/shortlist_report_{ts}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_build(results, jd_parsed))
    return path


def _color(s: float) -> str:
    return "#4caf7d" if s >= 7 else "#f5c842" if s >= 5 else "#e05c5c"


def _bar(s: float, color: str) -> str:
    return f'<div class="bar-bg"><div class="bar-fill" style="width:{int(s*10)}%;background:{color}"></div></div>'


def _build(results: list, jd_parsed: dict) -> str:
    role     = jd_parsed.get("role_title", "Position")
    domain   = jd_parsed.get("domain", "")
    seniority = jd_parsed.get("seniority_level", "")
    skills   = ", ".join(jd_parsed.get("required_skills", [])[:10])
    now      = datetime.now().strftime("%B %d, %Y at %H:%M")
    hire_n   = sum(1 for c in results if "hire" in c.get("recommendation","").lower() and "no" not in c.get("recommendation","").lower())
    avg      = sum(c.get("total_score", 0) for c in results) / max(len(results), 1)

    cards = ""
    for idx, c in enumerate(results):
        name  = c.get("name", f"Candidate {idx+1}")
        total = c.get("total_score", 0)
        rec   = c.get("recommendation", "No Hire")
        summ  = c.get("summary", "")
        src   = c.get("source", "")
        dims  = c.get("dimensions", {})
        tc    = _color(total)
        is_hire = "hire" in rec.lower() and "no" not in rec.lower()
        badge = '<span class="badge-hire">Hire</span>' if is_hire else '<span class="badge-nohire">No Hire</span>'

        dim_rows = ""
        for key, (label, weight) in DIMS.items():
            d  = dims.get(key, {})
            s  = d.get("score", 0)
            j  = d.get("justification", "")
            sc = _color(s)
            dim_rows += f"""
            <tr>
              <td>{label}</td><td>{weight}%</td>
              <td style="color:{sc};font-weight:700">{s}/10</td>
              <td style="min-width:120px">{_bar(s, sc)}</td>
              <td class="just">{j}</td>
            </tr>"""

        override = ""
        if c.get("overridden"):
            override = f'<div class="override">Override applied: {c.get("override_reason","")}</div>'

        cards += f"""
        <div class="card">
          <div class="card-head">
            <div class="rank">#{idx+1}</div>
            <div class="meta">
              <div class="cname">{name}</div>
              <div class="csrc">Source: {src}</div>
            </div>
            <div class="score-wrap">
              <div class="score" style="color:{tc}">{total:.1f}<span>/10</span></div>
              {badge}
            </div>
          </div>
          <p class="summary">{summ}</p>
          {override}
          <table class="dtable">
            <thead><tr><th>Dimension</th><th>Weight</th><th>Score</th><th>Bar</th><th>Justification</th></tr></thead>
            <tbody>{dim_rows}</tbody>
          </table>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HR Shortlist Report — {role}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:#0f0f13;color:#e8e4dd;padding:2rem}}
h1,h2{{font-family:'DM Serif Display',serif}}

.header{{background:linear-gradient(135deg,#1a1a24,#12121a);border:1px solid #2a2a3a;border-radius:16px;padding:2.5rem;margin-bottom:2rem}}
.title{{font-size:2rem;background:linear-gradient(90deg,#f5c842,#f0956a);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:#7a7a8a;margin-top:0.4rem;font-size:0.9rem}}
.meta-row{{display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap}}
.meta-pill{{background:#16161f;border:1px solid #2a2a3a;border-radius:8px;padding:0.4rem 1rem;font-size:0.85rem;color:#7a7a8a}}
.meta-pill strong{{color:#e8e4dd}}

.stats{{display:flex;gap:1rem;margin-bottom:2rem}}
.stat{{flex:1;background:#16161f;border:1px solid #2a2a3a;border-radius:12px;padding:1.2rem;text-align:center}}
.stat-n{{font-size:1.8rem;font-weight:700;color:#f5c842}}
.stat-l{{font-size:0.78rem;color:#7a7a8a;margin-top:4px}}

.sec{{font-size:1rem;font-weight:600;color:#f5c842;border-bottom:1px solid #2a2a3a;padding-bottom:0.4rem;margin-bottom:1.25rem}}

.card{{background:#16161f;border:1px solid #2a2a3a;border-radius:14px;padding:1.5rem;margin-bottom:1.5rem}}
.card-head{{display:flex;align-items:center;gap:1rem;margin-bottom:1rem}}
.rank{{background:linear-gradient(135deg,#f5c842,#f0956a);color:#0f0f13;border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}}
.meta{{flex:1}}
.cname{{font-size:1.15rem;font-weight:600;font-family:'DM Serif Display',serif}}
.csrc{{font-size:0.75rem;color:#5a5a6a;margin-top:2px}}
.score-wrap{{text-align:right}}
.score{{font-size:1.8rem;font-weight:700;line-height:1}}
.score span{{font-size:0.9rem;color:#5a5a6a}}
.badge-hire{{background:#1a3a28;color:#4caf7d;border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:600;display:inline-block;margin-top:4px}}
.badge-nohire{{background:#3a1a1a;color:#e05c5c;border-radius:20px;padding:2px 12px;font-size:0.75rem;font-weight:600;display:inline-block;margin-top:4px}}
.summary{{color:#9a9aaa;font-size:0.88rem;margin-bottom:1rem;line-height:1.6}}
.override{{background:#2a2010;border:1px solid #5a4010;border-radius:8px;padding:0.5rem 1rem;font-size:0.8rem;color:#c8a840;margin-bottom:1rem}}

.dtable{{width:100%;border-collapse:collapse;font-size:0.83rem}}
.dtable th{{text-align:left;padding:0.45rem 0.7rem;color:#5a5a6a;border-bottom:1px solid #2a2a3a;font-weight:500}}
.dtable td{{padding:0.5rem 0.7rem;border-bottom:1px solid #1a1a2a;vertical-align:middle}}
.dtable tr:last-child td{{border-bottom:none}}
.just{{color:#7a7a8a;font-size:0.78rem}}
.bar-bg{{background:#2a2a3a;border-radius:4px;height:8px}}
.bar-fill{{height:8px;border-radius:4px}}

.footer{{text-align:center;color:#3a3a4a;font-size:0.75rem;margin-top:3rem}}
</style>
</head>
<body>

<div class="header">
  <div class="title">HR Shortlist Report</div>
  <div class="sub">Generated {now}</div>
  <div class="meta-row">
    <div class="meta-pill"><strong>Role:</strong> {role}</div>
    <div class="meta-pill"><strong>Domain:</strong> {domain}</div>
    <div class="meta-pill"><strong>Seniority:</strong> {seniority}</div>
    <div class="meta-pill"><strong>Required Skills:</strong> {skills}</div>
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="stat-n">{len(results)}</div><div class="stat-l">Evaluated</div></div>
  <div class="stat"><div class="stat-n" style="color:#4caf7d">{hire_n}</div><div class="stat-l">Recommended Hire</div></div>
  <div class="stat"><div class="stat-n" style="color:#e05c5c">{len(results)-hire_n}</div><div class="stat-l">Not Recommended</div></div>
  <div class="stat"><div class="stat-n">{avg:.1f}</div><div class="stat-l">Average Score</div></div>
</div>

<div class="sec">Ranked Candidates</div>
{cards}

<div class="footer">
  HR Shortlisting Agent &nbsp;|&nbsp; Llama3 via Ollama &nbsp;|&nbsp; {now}<br>
  This report is AI-assisted. Final hiring decisions must be made by qualified HR professionals.
</div>
</body>
</html>"""
