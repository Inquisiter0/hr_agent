"""
create_session.py — Run this ONCE to create your LinkedIn session file.

Usage:
  python create_session.py

What it does:
  1. Opens a real Chromium browser window (not headless)
  2. Navigates to linkedin.com/login
  3. Polls every 2 seconds until you're logged in (up to 10 minutes)
  4. Saves your session cookies to session.json
  5. Closes the browser

After this, the main app uses session.json for all LinkedIn scraping
without needing to log in again (sessions typically last weeks).

Security note:
  session.json contains your LinkedIn auth cookies.
  - Never commit it to git (it's in .gitignore)
  - Never share it with anyone
  - If compromised, log out all LinkedIn sessions from your account settings
"""
import asyncio
import json
import sys
from pathlib import Path

SESSION_FILE = "session.json"
TIMEOUT_SECONDS = 600   # 10 minutes — plenty of time for 2FA etc.
POLL_INTERVAL   = 2     # check every 2 seconds


async def create_session():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright is not installed.")
        print("   Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=" * 60)
    print("  LinkedIn Session Creator")
    print("=" * 60)
    print()
    print("A browser window will open.")
    print("  1. Log in to LinkedIn with your credentials")
    print("  2. Complete any 2FA / CAPTCHA if prompted")
    print("  3. Once you see your LinkedIn feed, this script")
    print("     will detect it and save the session automatically.")
    print()
    print(f"⏳ You have {TIMEOUT_SECONDS // 60} minutes. Take your time.")
    print()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        # Poll until we land on a post-login page
        elapsed = 0
        logged_in = False
        while elapsed < TIMEOUT_SECONDS:
            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

            current_url = page.url
            # LinkedIn redirects to /feed or /in/<username> after login
            if any(x in current_url for x in ["/feed", "/mynetwork", "/jobs", "/messaging", "/in/"]):
                logged_in = True
                break

            # Also check if the nav bar (li-icon or global-nav) is present — login is done
            try:
                nav = await page.query_selector("[data-test-global-nav-link], .global-nav__me-photo, #global-nav")
                if nav:
                    logged_in = True
                    break
            except Exception:
                pass

            if elapsed % 30 == 0:
                remaining = TIMEOUT_SECONDS - elapsed
                print(f"  Still waiting… {remaining}s remaining. Current page: {current_url[:60]}")

        if not logged_in:
            print()
            print("❌ Timed out waiting for login.")
            print("   Please run the script again and log in within 10 minutes.")
            await browser.close()
            sys.exit(1)

        print("✅ Login detected! Saving session...")
        await asyncio.sleep(1)  # let cookies settle

        # Save cookies as JSON (Playwright storage state format)
        storage = await context.storage_state()
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(storage, f, indent=2)

        await browser.close()

    if Path(SESSION_FILE).exists():
        size = Path(SESSION_FILE).stat().st_size
        print(f"✅ Session saved → '{SESSION_FILE}' ({size:,} bytes)")
        print()
        print("You can now run the main app:")
        print("  streamlit run app.py")
        print()
        print("Note: If scraping fails with an auth error later,")
        print("      just re-run this script to refresh your session.")
    else:
        print("❌ Session file was not created. Something went wrong.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_session())
