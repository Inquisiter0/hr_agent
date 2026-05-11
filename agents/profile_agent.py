# profile_agent.py
import json
import io
import re
from utils.sanitizer import sanitize_text


def parse_resume(file_obj) -> dict:
    filename = file_obj.name.lower()
    if filename.endswith(".pdf"):
        raw_text = _extract_pdf(file_obj)
    elif filename.endswith(".docx"):
        raw_text = _extract_docx(file_obj)
    else:
        raise ValueError(f"Unsupported file type: {file_obj.name}")

    return {
        "type": "resume",
        "raw_text": sanitize_text(raw_text),
        "name": _extract_name(raw_text, file_obj.name),
        "source_file": file_obj.name,
    }


def parse_linkedin_json(file_obj) -> dict:
    content = file_obj.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_obj.name}: {e}")

    if isinstance(data, list):
        data = data[0] if data else {}

    parts = []

    # name
    name = (
        (data.get("firstName", "") + " " + data.get("lastName", "")).strip()
        or data.get("name", "Unknown")
    )
    parts.append(f"Name: {name}")

    # headline / summary
    for field in ("headline", "title", "summary", "about"):
        val = data.get(field, "")
        if val:
            parts.append(f"{field.capitalize()}: {val}")
            break

    # experience
    experiences = data.get("experience", data.get("positions", {}).get("values", []))
    for exp in experiences:
        title   = exp.get("title", "")
        company = exp.get("companyName", exp.get("company", {}).get("name", ""))
        tp      = exp.get("timePeriod", {})
        start   = tp.get("startDate", {})
        end     = tp.get("endDate", {})
        s_str   = f"{start.get('month','')}/{start.get('year','')}" if start else ""
        e_str   = f"{end.get('month','')}/{end.get('year','')}" if end else "Present"
        desc    = exp.get("description", "")
        parts.append(f"Experience: {title} at {company} ({s_str} - {e_str}). {desc}")

    # education
    for edu in data.get("education", []):
        school = edu.get("schoolName", "")
        degree = edu.get("degreeName", "")
        field  = edu.get("fieldOfStudy", "")
        parts.append(f"Education: {degree} in {field} from {school}")

    # skills
    skills = data.get("skills", [])
    if skills:
        names = [s.get("name", "") if isinstance(s, dict) else s for s in skills]
        parts.append(f"Skills: {', '.join(filter(None, names))}")

    # certifications
    for cert in data.get("certifications", []):
        parts.append(f"Certification: {cert.get('name', str(cert))}")

    return {
        "type": "linkedin",
        "raw_text": sanitize_text("\n".join(parts)),
        "name": name,
        "source_file": file_obj.name,
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_pdf(file_obj) -> str:
    try:
        import pdfplumber
        file_obj.seek(0)
        with pdfplumber.open(io.BytesIO(file_obj.read())) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        pass
    try:
        import PyPDF2
        file_obj.seek(0)
        reader = PyPDF2.PdfReader(io.BytesIO(file_obj.read()))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    except ImportError:
        pass
    raise ImportError("Install pdfplumber: pip install pdfplumber")


def _extract_docx(file_obj) -> str:
    try:
        import docx
        file_obj.seek(0)
        doc = docx.Document(io.BytesIO(file_obj.read()))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        raise ImportError("Install python-docx: pip install python-docx")


def _extract_name(text: str, filename: str) -> str:
    for line in text.strip().splitlines():
        line = line.strip()
        if line and len(line.split()) <= 5 and not any(c.isdigit() for c in line):
            return line
    return re.sub(r"[_\-]", " ", filename.rsplit(".", 1)[0]).title()
