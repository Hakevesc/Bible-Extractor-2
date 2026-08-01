"""
STEP Bible Amharic scraper using Selenium + improved verse extraction logic.

The browser DOM (unlike the raw REST API response) contains verse spans with a
`data-osisid` attribute (e.g. "Matt.1.22"). We target those spans and exclude
footnote / cross-reference text, per the improved extraction approach.

If Selenium / a real browser is unavailable (e.g. Streamlit Community Cloud),
we automatically fall back to the STEP Bible REST API, which returns the same
verse text but without footnote contamination.
"""
import html
import os
import re
import time

import requests

STEP_BASE = "https://www.stepbible.org"
STEP_REST_TEXT = STEP_BASE + "/rest/bible/getBibleText"
STEP_WEB_URL = STEP_BASE + "/?q=version=AmhNASV@reference={ref}"

AMHARIC_VERSION = "AmhNASV"

# ---------------------------------------------------------------------------
# Book reference handling
# ---------------------------------------------------------------------------

# Map our book id (1-66) to the OSIS book abbreviation used by STEP Bible.
# These match STEPBible's canonical OSIS IDs (e.g. "Matt", "Gen", "1Sam").
BOOK_OSIS = {
    1: "Gen", 2: "Exod", 3: "Lev", 4: "Num", 5: "Deut",
    6: "Josh", 7: "Judg", 8: "Ruth", 9: "1Sam", 10: "2Sam",
    11: "1Kgs", 12: "2Kgs", 13: "1Chr", 14: "2Chr", 15: "Ezra",
    16: "Neh", 17: "Esth", 18: "Job", 19: "Ps", 20: "Prov",
    21: "Eccl", 22: "Song", 23: "Isa", 24: "Jer", 25: "Lam",
    26: "Ezek", 27: "Dan", 28: "Hos", 29: "Joel", 30: "Amos",
    31: "Obad", 32: "Jonah", 33: "Mic", 34: "Nah", 35: "Hab",
    36: "Zeph", 37: "Hag", 38: "Zech", 39: "Mal",
    40: "Matt", 41: "Mark", 42: "Luke", 43: "John", 44: "Acts",
    45: "Rom", 46: "1Cor", 47: "2Cor", 48: "Gal", 49: "Eph",
    50: "Phil", 51: "Col", 52: "1Thess", 53: "2Thess", 54: "1Tim",
    55: "2Tim", 56: "Titus", 57: "Phlm", 58: "Heb", 59: "Jas",
    60: "1Pet", 61: "2Pet", 62: "1John", 63: "2John", 64: "3John",
    65: "Jude", 66: "Rev",
}

# Standard 66-book Protestant chapter counts, aligned with book id (1-66).
BOOK_CHAPTERS = {
    1: 50, 2: 40, 3: 27, 4: 36, 5: 34, 6: 24, 7: 21, 8: 4,
    9: 31, 10: 24, 11: 22, 12: 25, 13: 29, 14: 36, 15: 10, 16: 13,
    17: 10, 18: 42, 19: 150, 20: 31, 21: 12, 22: 8, 23: 66, 24: 52,
    25: 5, 26: 48, 27: 12, 28: 14, 29: 3, 30: 9, 31: 1, 32: 4,
    33: 7, 34: 3, 35: 3, 36: 3, 37: 2, 38: 14, 39: 4,
    40: 28, 41: 16, 42: 24, 43: 21, 44: 28, 45: 16, 46: 16, 47: 13,
    48: 6, 49: 6, 50: 4, 51: 4, 52: 5, 53: 3, 54: 6, 55: 4,
    56: 3, 57: 1, 58: 13, 59: 5, 60: 5, 61: 3, 62: 5, 63: 1,
    64: 1, 65: 1, 66: 22,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_selenium_available():
    """Return True only if a real browser can be driven via Selenium.

    Always returns False on hosted platforms (Streamlit Cloud etc.) and when
    STEP_FORCE_REST=1 is set, so the fast REST path is used and the app can
    never hang waiting for a browser during startup.
    """
    # Hosted platforms: never attempt Selenium (no browser / could hang).
    if os.environ.get("STREAMLIT_RUNTIME"):
        return False
    # Explicit override: always use the REST API.
    if os.environ.get("STEP_FORCE_REST", "").strip().lower() in ("1", "true", "yes"):
        return False

    try:
        from selenium import webdriver  # noqa: F401
        from selenium.webdriver.chrome.options import Options  # noqa: F401
    except Exception:
        return False

    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    return any(os.path.exists(c) for c in chrome_candidates)


def get_chapter(book_id, chapter):
    """Try Selenium first; fall back to the REST API when no browser exists."""
    if check_selenium_available():
        try:
            return get_chapter_selenium(book_id, chapter)
        except Exception:
            # Fall through to the REST API on any Selenium/browser failure
            pass
    return get_chapter_rest(book_id, chapter)


def _extract_verse_number_from_osis(osis_id):
    """Return the verse number from an OSIS ID like 'Matt.1.22'."""
    if not osis_id:
        return 0
    parts = osis_id.split(".")
    if len(parts) < 3:
        return 0
    try:
        return int(parts[-1])
    except ValueError:
        return 0


def parse_verse_span(el_text):
    """
    Clean a single verse element's raw text into the actual verse content.

    - Removes footnote markers and everything after them.
    - Removes cross-reference patterns.
    - Collapses whitespace.
    """
    raw_text = str(el_text)
    # STEP Bible uses ▼ (and sometimes ^) as footnote markers
    for marker in ("▼", "^"):
        if marker in raw_text:
            raw_text = raw_text.split(marker)[0]
    # Remove leading verse-number superscripts that may appear as text
    raw_text = re.sub(r"^\s*\d{1,3}\s+", "", raw_text)
    # Normalise whitespace
    clean = re.sub(r"\s+", " ", raw_text).strip()
    return clean


# ---------------------------------------------------------------------------
# Selenium-based extraction (improved logic: span[data-osisid])
# ---------------------------------------------------------------------------

def get_chapter_selenium(book_id, chapter):
    """
    Load the STEP Bible page for the given book/chapter in a real browser and
    extract verses using `span[data-osisid]`, excluding footnote content.

    Returns a list of {"book": book_id, "chapter": chapter, "verse": n,
    "text": "..."}.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    osis_book = BOOK_OSIS.get(book_id)
    if not osis_book:
        raise ValueError(f"Unknown book id: {book_id}")

    url = STEP_WEB_URL.format(ref=f"{osis_book}.{chapter}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1400,1200")
    options.add_argument("--lang=en")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        # Wait for STEP Bible's JavaScript to render the OSIS verse spans.
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "span[data-osisid]")
            )
        )
        time.sleep(2)  # small extra wait for the JS to decorate the DOM fully

        verse_elements = driver.find_elements(
            By.CSS_SELECTOR, "span[data-osisid]"
        )
        verses = []
        for el in verse_elements:
            osis_id = el.get_attribute("data-osisid")
            verse_num = _extract_verse_number_from_osis(osis_id)

            raw_text = el.text
            clean_text = parse_verse_span(raw_text)

            # Skip empty / footnote-only / cross-reference-only fragments.
            if clean_text and len(clean_text) > 10:
                verses.append({
                    "book": book_id,
                    "chapter": chapter,
                    "verse": verse_num if verse_num else 0,
                    "text": clean_text,
                })
        return verses
    finally:
        driver.quit()


# ---------------------------------------------------------------------------
# REST API fallback (identical verse text, works on Streamlit Cloud)
# ---------------------------------------------------------------------------

def get_chapter_rest(book_id, chapter):
    """
    Fetch a chapter from the STEP Bible REST API.

    The API returns clean verse spans (class='verse ltrDirection') without
    footnote/cross-reference contamination. Callers receive a list of
    {"book": book_id, "chapter": chapter, "verse": n, "text": "..."}.
    """
    osis_book = BOOK_OSIS.get(book_id)
    if not osis_book:
        raise ValueError(f"Unknown book id: {book_id}")

    ref = f"{osis_book}.{chapter}"
    url = f"{STEP_REST_TEXT}/{AMHARIC_VERSION}/{ref}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if data.get("errorMessage"):
        raise RuntimeError(data["errorMessage"])

    raw_html = data.get("value", "")
    # Each verse is a <span ... class='verse ltrDirection'>...</span>.
    # In the AmhNASV text, verses are rendered as a flat sequence of these
    # spans within the chapter.
    verse_spans = re.findall(
        r"<span[^>]*class='verse ltrDirection'[^>]*>(.*?)</span>",
        raw_html,
        re.DOTALL,
    )

    verses = []
    for idx, span in enumerate(verse_spans, start=1):
        text = re.sub(r"<[^>]+>", "", span)      # strip inner HTML tags
        text = html.unescape(text)               # decode entities
        text = re.sub(r"\s+", " ", text).strip()  # normalise whitespace
        if text:
            verses.append({
                "book": book_id,
                "chapter": chapter,
                "verse": idx,
                "text": text,
            })
    return verses


def get_book_verses(book_id, book_name):
    """
    Fetch all chapters of a book and return a flat list of verse dicts with
    keys: book_name, book, chapter, verse, text.
    """
    chapter_count = BOOK_CHAPTERS.get(book_id)
    if not chapter_count:
        raise ValueError(f"Unknown book id: {book_id}")

    all_verses = []
    for chapter in range(1, chapter_count + 1):
        chapter_verses = get_chapter(book_id, chapter)
        for v in chapter_verses:
            v["book_name"] = book_name
            all_verses.append(v)
    return all_verses


# Small self-test helper for quick CLI verification
if __name__ == "__main__":
    # When this module is run directly (e.g. as a Streamlit main file, or a
    # plain CLI script), detect the environment:
    try:
        import streamlit  # noqa: F401
        try:
            from streamlit.runtime import exists as _st_runtime_exists
            is_streamlit = bool(_st_runtime_exists())
        except Exception:
            is_streamlit = os.environ.get("STREAMLIT_RUNTIME", "").strip().lower() \
                in ("1", "true", "yes")
    except Exception:
        is_streamlit = False

    if is_streamlit:
        # Running as a Streamlit app -> launch the full UI.
        import app
        app.main()
    else:
        # Plain CLI self-test.
        import sys

        test_book = int(sys.argv[1]) if len(sys.argv) > 1 else 40  # Matt
        test_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        test_name = "ማቴዎስ" if test_book == 40 else BOOK_OSIS.get(test_book, "?")

        print(f"Fetching {BOOK_OSIS.get(test_book)} {test_ch} via "
              f"{'Selenium' if check_selenium_available() else 'REST API'} ...")
        verses = get_chapter(test_book, test_ch)
        print(f"Got {len(verses)} verses")
        for v in verses:
            if v["verse"] == 22:
                print("Verse 22:", v["text"])
                break
        if test_book == 40:
            all_v = get_book_verses(40, test_name)
            print(f"Full Matthew: {len(all_v)} verses, "
                  f"first: {all_v[0]['text'][:30]}...")
