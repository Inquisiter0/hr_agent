# sanitizer.py — prompt injection defense
import re

_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(if\s+you\s+are|an?\s+)",
    r"new\s+instruction[s]?:",
    r"system\s+prompt:",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"\[/INST\]",
    r"###\s*instruction",
    r"override\s+(safety|guidelines|rules)",
    r"jailbreak",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def sanitize_text(text: str, max_length: int = 12000) -> str:
    if not isinstance(text, str):
        text = str(text)
    # strip control chars (keep \n \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    for pattern in _COMPILED:
        text = pattern.sub("[FILTERED]", text)
    if len(text) > max_length:
        text = text[:max_length] + "\n[TRUNCATED]"
    return text.strip()
