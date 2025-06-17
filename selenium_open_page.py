from __future__ import annotations

"""
Saudi Exchange scraper — full article grabber
─────────────────────────────────────────────
For every article across all pages:
1. Prints **date | title | url** while on the listing page.
2. Opens the article in a background tab, extracts its body text, and looks for
   downloadable attachments (PDF, DOCX, XLSX, etc.). Any found files are saved
   into `./downloads/` and their local paths are printed.

→ Run with:
    python selenium_open_page.py "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports" --show

Add `--keep` to keep the browser open after completion.
"""

from typing import List, Dict
import sys
import os
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from datetime import datetime

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
WAIT_SECS = 25  # generous, because the site can be slow
BASE_URL = "https://www.saudiexchange.sa"
DOWNLOAD_DIR = Path("downloads")

# File extensions we consider downloadable
DL_EXT_PATTERN = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip)$", re.I)

# ────────────────────────────────────────────────────────────────────────────────
# Browser setup helpers
# ────────────────────────────────────────────────────────────────────────────────

def build_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")

    opts.add_argument(f"--user-agent={USER_AGENT}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        },
    )
    return driver

# ────────────────────────────────────────────────────────────────────────────────
# Listing‑page helpers
# ────────────────────────────────────────────────────────────────────────────────

def click_period(driver: webdriver.Chrome, period_id: str = "1D") -> None:
    anchor = WebDriverWait(driver, WAIT_SECS).until(
        EC.element_to_be_clickable((By.ID, period_id))
    )
    anchor.click()
    print(f"✔ Clicked period button id='{period_id}'.")


def extract_list_items(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """Return [{'date', 'title', 'url'} …] from current listing page."""
    try:
        WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#announcementResultsDivId li"))
        )
    except TimeoutException:
        return []

    items: List[Dict[str, str]] = []
    for li in driver.find_elements(By.CSS_SELECTOR, "#announcementResultsDivId li"):
        try:
            title = li.find_element(By.TAG_NAME, "h2").text.strip()
            date_str = li.find_element(By.CSS_SELECTOR, "div.date").text.strip()
            anchor = li.find_element(By.XPATH, "..")  # parent <a>
            href = urljoin(BASE_URL, anchor.get_attribute("href"))
            items.append({"date": date_str, "title": title, "url": href})
        except NoSuchElementException:
            continue
    return items


def goto_next_page(driver: webdriver.Chrome) -> bool:
    """Click ›. Returns False if disabled OR new page fails to load."""
    try:
        next_li = driver.find_element(By.ID, "next-toggle-id")
    except NoSuchElementException:
        return False

    if "disable" in next_li.get_attribute("class"):
        return False  # on last page

    old_ul = driver.find_element(By.ID, "announcementResultsDivId")
    current_page = driver.find_element(By.CSS_SELECTOR, "#pagination-ul .px-btn-page.select").get_attribute("data-page")
    next_li.find_element(By.TAG_NAME, "a").click()

    wait = WebDriverWait(driver, WAIT_SECS)
    try:
        wait.until(EC.staleness_of(old_ul))
        wait.until(
            lambda d: d.find_element(By.CSS_SELECTOR, "#pagination-ul .px-btn-page.select").get_attribute("data-page") != current_page
        )
        return True
    except TimeoutException:
        return False

# ────────────────────────────────────────────────────────────────────────────────
# Article‑page helpers
# ────────────────────────────────────────────────────────────────────────────────

def sanitize_name(name: str, is_dir: bool = False) -> str:
    """Sanitizes a string for use as a valid filename or directory name."""
    name = unquote(name)
    invalid_chars = r'[\\/:*?"<>|]'
    name = re.sub(invalid_chars, "_", name)
    if is_dir:
        name = name.replace('.', '_')
    name = re.sub(r'\s+', '_', name)
    return name[:120] or ("directory" if is_dir else "file")


def download_attachments(page_url: str, driver: webdriver.Chrome, article_dir: Path) -> List[str]:
    """
    Finds all downloadable links on the page and saves them into `article_dir`.
    Returns a list of local file paths.
    """
    paths: List[str] = []
    for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
        href = a.get_attribute("href")
        if not href or not DL_EXT_PATTERN.search(href):
            continue

        full_url = urljoin(page_url, href)
        filename_part = os.path.basename(urlparse(full_url).path)
        filename = sanitize_name(filename_part)
        dest = article_dir / filename

        if dest.exists():
            continue
        try:
            resp = requests.get(full_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            paths.append(str(dest))
        except Exception as e:
            print(f"⚠ Failed to download {full_url}: {e}")
    return paths


def scrape_article(driver: webdriver.Chrome, article: Dict[str, str]) -> None:
    """
    Opens article in a new tab, grabs body text + attachments, and saves everything
    into a structured directory, then closes the tab.
    """
    # 1. Create the directory structure based on date and article title
    today_str = datetime.now().strftime("%Y-%m-%d")
    article_title_safe = sanitize_name(article["title"], is_dir=True)
    article_dir = DOWNLOAD_DIR / today_str / article_title_safe
    article_dir.mkdir(parents=True, exist_ok=True)

    # 2. Open article in a new tab
    parent = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", article["url"])
    WebDriverWait(driver, WAIT_SECS).until(lambda d: len(d.window_handles) > 1)
    new_tab = [h for h in driver.window_handles if h != parent][0]
    driver.switch_to.window(new_tab)

    try:
        WebDriverWait(driver, WAIT_SECS).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # 3. Extract main text and save to a file
        paragraphs = (
            driver.find_elements(By.CSS_SELECTOR, "main p") or driver.find_elements(By.TAG_NAME, "p")
        )
        body_text = "\n".join(p.text.strip() for p in paragraphs if p.text.strip())

        article_txt_path = article_dir / "article.txt"
        article_txt_path.write_text(body_text, encoding="utf-8")

        print(f"\n✔ Saved: {article['title']}")
        print(f"  - Directory: {article_dir}")

        # 4. Download attachments into the same directory
        files = download_attachments(article["url"], driver, article_dir)
        for f in files:
            print(f"  - Attachment: {f}")

    finally:
        driver.close()
        driver.switch_to.window(parent)

# ────────────────────────────────────────────────────────────────────────────────
# Main logic
# ────────────────────────────────────────────────────────────────────────────────

def main(url: str, *, headless: bool = True, keep_open: bool = False) -> None:
    drv = build_driver(headless)
    try:
        drv.get(url)
        WebDriverWait(drv, WAIT_SECS).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        if drv.title.lower().startswith("access denied"):
            print("‼ Access denied — aborting.")
            return

        click_period(drv, "1D")

        page_no = 1
        while True:
            print(f"\n==== LIST PAGE {page_no} ====")
            articles = extract_list_items(drv)
            if not articles:
                print("Empty page — stopping.")
                break
            for art in articles:
                print(f"{art['date']} | {art['title']} | {art['url']}")
            for art in articles:
                scrape_article(drv, art)
            page_no += 1
            if not goto_next_page(drv):
                break

        print("\n✔ Done.")
        if keep_open:
            input("\nPress <Enter> to close browser…")
    finally:
        drv.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python selenium_open_page.py <URL> [--show] [--keep]")
        sys.exit(1)

    target_url = sys.argv[1]
    show_ui = "--show" in sys.argv[2:]
    hold_open = "--keep" in sys.argv[2:]
    main(target_url, headless=not show_ui, keep_open=hold_open)
