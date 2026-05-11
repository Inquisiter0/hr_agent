"""
LinkedIn Scraper — linkedin-scraper PyPI package (v3.0+, Playwright-based)
https://pypi.org/project/linkedin-scraper/

Requires:
  pip install linkedin-scraper
  playwright install chromium

Also requires a saved LinkedIn session file (session.json).
Run `python create_session.py` once to generate it interactively.
"""
import asyncio
import os
from pathlib import Path
from utils.sanitizer import sanitize_text

# Default session file path — can be overridden via LINKEDIN_SESSION_PATH env var
DEFAULT_SESSION = os.getenv("LINKEDIN_SESSION_PATH", "session.json")


def scrape_linkedin_profile(profile_url: str, session_path: str = DEFAULT_SESSION) -> dict:
    """
    Synchronous wrapper around the async scraper.
    Called from Streamlit (which runs in a regular sync context).

    Args:
        profile_url:   Full LinkedIn profile URL, e.g. https://www.linkedin.com/in/username/
        session_path:  Path to session.json created by create_session.py

    Returns:
        Unified profile dict with keys: type, raw_text, name, source_file
    """
    _check_session_file(session_path)
    url = _normalize_linkedin_url(profile_url)
    return asyncio.run(_async_scrape(url, session_path))


async def _async_scrape(url: str, session_path: str) -> dict:
    """Core async scraping logic — loads Playwright storage_state session, then uses PersonScraper."""
    try:
        from playwright.async_api import async_playwright
        from linkedin_scraper import PersonScraper
    except ImportError:
        raise ImportError(
            "Required packages not installed.\n"
            "Run: pip install linkedin-scraper playwright && playwright install chromium"
        )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        # Load cookies from the session file created by create_session.py
        context = await browser.new_context(
            storage_state=session_path,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # Quick auth check before scraping
        await page.goto("https://www.linkedin.com/feed", wait_until="domcontentloaded", timeout=20000)
        if "login" in page.url or "authwall" in page.url:
            await browser.close()
            raise RuntimeError(
                "LinkedIn session expired or invalid. "
                "Re-run `python create_session.py` to refresh session.json."
            )

        scraper = PersonScraper(page)

        try:
            person = await scraper.scrape(url)
        except Exception as e:
            err = str(e).lower()
            await browser.close()
            if "rate" in err or "429" in err:
                raise RuntimeError("LinkedIn rate-limited this request. Wait a few minutes and try again.")
            if "not found" in err or "404" in err or "private" in err:
                raise RuntimeError(f"Profile not found or private: {url}")
            raise RuntimeError(f"Scraping failed for {url}: {e}")

        await browser.close()

    return _normalize_person(person, url)


def _normalize_person(person, url: str) -> dict:
    """Convert a linkedin-scraper Person Pydantic model to our unified profile dict."""
    parts = []

    name = getattr(person, "name", "") or "Unknown"
    parts.append(f"Name: {name}")

    headline = getattr(person, "headline", "")
    if headline:
        parts.append(f"Headline: {headline}")

    location = getattr(person, "location", "")
    if location:
        parts.append(f"Location: {location}")

    about = getattr(person, "about", "")
    if about:
        parts.append(f"Summary: {about}")

    # Experiences — v3.0 uses position_title / institution_name / from_date / to_date
    for exp in getattr(person, "experiences", []) or []:
        title       = getattr(exp, "position_title", None) or getattr(exp, "title", "")
        company     = getattr(exp, "institution_name", None) or getattr(exp, "company", "")
        from_date   = getattr(exp, "from_date", "")
        to_date     = getattr(exp, "to_date", "Present")
        description = getattr(exp, "description", "") or ""
        parts.append(f"Experience: {title} at {company} ({from_date} – {to_date}). {description}")

    # Education
    for edu in getattr(person, "educations", []) or []:
        school = getattr(edu, "institution_name", None) or getattr(edu, "school", "")
        degree = getattr(edu, "degree", "") or ""
        field  = getattr(edu, "field_of_study", None) or getattr(edu, "field", "") or ""
        parts.append(f"Education: {degree} in {field} from {school}")

    # Skills (List[str] in v3)
    skills = getattr(person, "skills", []) or []
    if skills:
        skill_strs = [s if isinstance(s, str) else getattr(s, "name", str(s)) for s in skills]
        parts.append(f"Skills: {', '.join(filter(None, skill_strs))}")

    # Accomplishments (publications, patents, courses, honors, projects, etc.)
    accomplishments = getattr(person, "accomplishments", None)
    if accomplishments:
        for key in ("publications", "patents", "courses", "honors", "projects"):
            items = getattr(accomplishments, key, []) or []
            for item in items:
                item_name = getattr(item, "name", None) or getattr(item, "title", str(item))
                parts.append(f"{key.capitalize()}: {item_name}")

    raw_text = "\n".join(parts)

    return {
        "type": "linkedin_live",
        "raw_text": sanitize_text(raw_text),
        "name": name,
        "source_file": url,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _check_session_file(session_path: str) -> None:
    """Raise a clear, actionable error if session.json doesn't exist."""
    if not Path(session_path).exists():
        raise FileNotFoundError(
            f"LinkedIn session file not found: '{session_path}'\n\n"
            "Run this ONCE to create it (opens a browser window):\n"
            "  python create_session.py\n\n"
            "Log in to LinkedIn in the browser, then the session is saved automatically."
        )


def _normalize_linkedin_url(url: str) -> str:
    """Ensure the URL is a clean https://www.linkedin.com/in/... URL."""
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    if "linkedin.com/in/" not in url:
        raise ValueError(
            f"Not a valid LinkedIn profile URL: {url}\n"
            "Expected format: https://www.linkedin.com/in/username"
        )
    return url + "/"
