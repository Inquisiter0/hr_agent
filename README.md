# HR Resume & LinkedIn Shortlisting Agent

An AI agent that evaluates candidates against a Job Description using a structured 5-dimension rubric, running via Groq API.

---

## Project Overview

1. Parses a Job Description into structured requirements
2. Ingests PDF/DOCX resumes and LinkedIn JSON exports
3. Scores each candidate across 5 weighted dimensions
4. Ranks candidates and generates an HTML report
5. Allows HR score overrides with a logged audit trail

---

## Agent Architecture

```
Streamlit UI (app.py)
        |
   ┌────┴────┐
   |         |
JD Parser   Profile Agent
(Llama3)    (pdfplumber / python-docx / JSON)
   |         |
   └────┬────┘
        |
   Score Agent
   (Llama3 — 5 dimensions)
        |
   Report Agent
   (HTML output)
        |
   Override Log
   (JSONL audit trail)
```

Agent pattern: Sequential pipeline
Input → Parse JD → Parse Profiles → Score → Rank → Report → [Human Override]

---



## Scoring Rubric

| Dimension | Weight | 0 – Poor | 5 – Average | 10 – Excellent |
|---|---|---|---|---|
| Skills Match | 30% | <30% skills match | 50–70% match | >85% match |
| Experience Relevance | 25% | Unrelated domain | Adjacent domain | Exact domain & seniority |
| Education & Certs | 15% | Below minimum | Meets minimum | Exceeds + extra certs |
| Project / Portfolio | 20% | No evidence | 1–2 generic projects | Strong relevant portfolio |
| Communication Quality | 10% | Poor structure | Adequate clarity | Crisp, structured, impactful |

Total = (Skills×0.30 + Experience×0.25 + Education×0.15 + Portfolio×0.20 + Communication×0.10)

Recommendation: Hire if total >= 6.0, else No Hire.

---

## Tech Stack & Decision Log

### LLM

| Item | Choice | Rationale |
|---|---|---|
| Model | Llama 3 8B via Groq | Fast inference, high quality |
| Temperature | 0.1 | Low temperature for deterministic structured JSON output |

### Agent Framework

Custom sequential pipeline using native Python.

### Resume Parsing

- pdfplumber (primary) → PyPDF2 (fallback) for PDFs
- python-docx for DOCX files

### LinkedIn Input

Candidate exports their own profile: LinkedIn → Settings → Data Privacy → Get a copy of your data → Profile → Request archive. The Profile.json from the downloaded zip is uploaded directly. No scraping, no third-party API, no ban risk.

### Output

- Self-contained HTML report
- JSONL append-only audit log for HR overrides (no database needed)

---

## Security Risk Mitigations

This section is mandatory per the brief and covers all listed risks.

| Risk | Mitigation |
|---|---|
| Prompt Injection | `utils/sanitizer.py` strips 12 injection patterns (ignore instructions, act as, jailbreak, system prompt, etc.) from all user-supplied text before it reaches the LLM. Injection defense is also stated in the system prompt itself. |
| Data Privacy / PII | LLM processing is handled via Groq. Override logs store only name and scores, not raw resume text. |
| API Key Exposure | API keys are managed securely via `.env`. `.env.example` provided as template. `.gitignore` excludes `.env` and `output/`. |
| Hallucination Risk | Structured JSON schema enforced in system prompt. `_validate()` in score_agent.py checks all scores are within [0,10]. Falls back to a safe zero-score result if parsing fails. |
| Unauthorised Access | Streamlit can be run with `--server.address localhost`. For production: add `streamlit-authenticator`. |
| Context Overflow Attack | `sanitize_text()` truncates all input to 12,000 chars. Score agent further truncates candidate text to 6,000 chars. |

---

## Setup

### Prerequisites

- Python 3.10+
- Groq API Key

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### LinkedIn JSON

Ask each candidate to:
1. Go to LinkedIn → Settings → Data Privacy → Get a copy of your data
2. Select "Profile data" → Request archive
3. Download the zip when ready → extract → upload Profile.json in the app

---

## Project Structure

```
hr_agent/
├── app.py                        # Streamlit UI
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── agents/
│   ├── jd_parser.py              # Parses JD into structured requirements via Llama3
│   ├── profile_agent.py          # Parses PDF/DOCX resumes and LinkedIn JSON
│   ├── score_agent.py            # Scores candidate across 5 dimensions via Llama3
│   └── report_agent.py           # Generates HTML report
├── utils/
│   ├── sanitizer.py              # Prompt injection defense
│   └── override_log.py           # JSONL audit trail
├── sample_data/
│   ├── priya_sharma_linkedin.json
│   └── rahul_verma_linkedin.json
└── output/                       # Reports and logs (gitignored)
```

---

## Prompt Design

JD Parser system prompt:
- Returns only valid JSON matching a fixed schema
- Ignores any commands embedded in JD text
- Temperature 0.1 for determinism

Score Agent system prompt:
- Explicit rubric with anchors (0=poor, 5=avg, 10=excellent)
- Hard rule: never score outside 0–10
- One-line justification required per dimension
- Exact weighted formula specified
- Recommendation threshold: >= 6.0 = Hire



## Disclaimer

This tool is AI-assisted. All final hiring decisions must be made by qualified HR professionals.
