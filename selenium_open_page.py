from __future__ import annotations

"""
Saudi Exchange scraper — Database integration version
─────────────────────────────────────────────────────
For every article across all pages:
1. Checks if the article URL is already in the database. If so, skips it.
2. If new, it opens the article, extracts its body text, and downloads attachments.
3. It then extracts text from the attachments (PDF, DOCX, XLSX).
4. Finally, it saves all gathered information into the 'articles' table in the
   SQLite database for later processing by an LLM.

→ Run with:
    python selenium_open_page.py "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports" --show
"""

from typing import List, Dict
import sys
import os
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from datetime import datetime

## NEW: Imports for database and text extraction
import sqlite3
import PyPDF2
import docx
import openpyxl

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
WAIT_SECS = 25
BASE_URL = "https://www.saudiexchange.sa"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True) # Ensure download directory exists

## NEW: Database file constant
DATABASE_FILE = "stock_news.db"

DL_EXT_PATTERN = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip)$", re.I)

# ────────────────────────────────────────────────────────────────────────────────
# Browser setup helpers (No changes here)
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
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver

# ────────────────────────────────────────────────────────────────────────────────
# Listing‑page helpers (No changes here)
# ────────────────────────────────────────────────────────────────────────────────

def click_period(driver: webdriver.Chrome, period_id: str = "1D") -> None:
    """
    Waits for the specified period filter button and clicks it.
    This version is more robust, using a JavaScript click and adding
    error handling with a screenshot for debugging.

    Args:
        driver: The Selenium WebDriver instance.
        period_id: The ID of the period button to click (e.g., '1D').
    """
    try:
        # Wait for the element to be present in the DOM, which is less strict
        # than being clickable.
        print(f"Attempting to click period button with id='{period_id}'...")
        anchor = WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.ID, period_id))
        )

        # Use JavaScript to click the element. This can bypass issues where
        # another element is covering the button, making it unclickable for Selenium.
        driver.execute_script("arguments[0].click();", anchor)
        print(f"✔ Clicked period button id='{period_id}'.")

    except TimeoutException:
        print(f"‼ Timed out waiting for period button with id='{period_id}'. The website may have changed.")
        
        # Save a screenshot of the page for manual inspection.
        # This helps diagnose if the button is missing, has a different ID, or if the page didn't load correctly.
        screenshot_path = "debug_screenshot.png"
        driver.save_screenshot(screenshot_path)
        print(f"  - A screenshot has been saved to '{screenshot_path}' for debugging.")
        
        # Re-raise the exception to halt the script, as it cannot proceed.
        raise

def extract_list_items(driver: webdriver.Chrome) -> List[Dict[str, str]]:
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
            anchor = li.find_element(By.XPATH, "..")
            href = urljoin(BASE_URL, anchor.get_attribute("href"))
            items.append({"date": date_str, "title": title, "url": href})
        except NoSuchElementException:
            continue
    return items

def goto_next_page(driver: webdriver.Chrome) -> bool:
    try:
        next_li = driver.find_element(By.ID, "next-toggle-id")
    except NoSuchElementException:
        return False
    if "disable" in next_li.get_attribute("class"):
        return False
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
## NEW: Database and Text Extraction Helpers
# ────────────────────────────────────────────────────────────────────────────────

def extract_text_from_file(filepath: Path) -> str:
    """Extracts text from PDF, DOCX, or XLSX files."""
    text = ""
    try:
        if filepath.suffix == '.pdf':
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        elif filepath.suffix == '.docx':
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif filepath.suffix == '.xlsx':
            workbook = openpyxl.load_workbook(filepath)
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value:
                            text += str(cell.value) + " "
                    text += "\n"
    except Exception as e:
        return f"[Error extracting text from {filepath.name}: {e}]"
    return text

def add_article_to_db(article_data: Dict[str, str]) -> bool:
    """
    Inserts a new article record into the database.
    Returns True if added, False if it was a duplicate.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    sql = """
        INSERT INTO articles (
            title, url, publication_date, article_text, attachments_text
        ) VALUES (?, ?, ?, ?, ?);
    """
    try:
        cursor.execute(sql, (
            article_data['title'],
            article_data['url'],
            article_data['date'],
            article_data['article_text'],
            article_data['attachments_text']
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This error occurs if the URL is not unique, which is what we want.
        return False
    finally:
        conn.close()

# ────────────────────────────────────────────────────────────────────────────────
## MODIFIED: Article Scraping Logic
# ────────────────────────────────────────────────────────────────────────────────

def scrape_article(driver: webdriver.Chrome, article_info: Dict[str, str]) -> None:
    """
    Opens an article, extracts all text from body and attachments,
    and saves it to the database. Skips if URL is already in the DB.
    """
    print(f"\nProcessing: {article_info['title']}")

    # 1. Open article in a new tab
    parent_handle = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", article_info["url"])
    WebDriverWait(driver, WAIT_SECS).until(EC.number_of_windows_to_be(2))
    new_tab_handle = [h for h in driver.window_handles if h != parent_handle][0]
    driver.switch_to.window(new_tab_handle)

    try:
        # Wait for page to load
        WebDriverWait(driver, WAIT_SECS).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main, body"))
        )

        # 2. Extract main body text from the page
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "main p") or driver.find_elements(By.TAG_NAME, "p")
        article_text = "\n".join(p.text.strip() for p in paragraphs if p.text.strip())

        # 3. Download attachments and extract their text
        attachments_text_parts = []
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = a.get_attribute("href")
            if not href or not DL_EXT_PATTERN.search(href):
                continue

            full_url = urljoin(article_info["url"], href)
            filename = unquote(os.path.basename(urlparse(full_url).path))
            dest = DOWNLOAD_DIR / filename

            try:
                # Download the file
                resp = requests.get(full_url, headers={"User-Agent": USER_AGENT}, timeout=45)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                print(f"  - Downloaded: {dest}")

                # Extract text from the downloaded file
                file_text = extract_text_from_file(dest)
                attachments_text_parts.append(f"--- CONTENT FROM {filename} ---\n{file_text}")

            except Exception as e:
                print(f"  ⚠ Failed to download or process {full_url}: {e}")

        # 4. Combine all data and save to database
        full_article_data = {
            **article_info,
            "article_text": article_text,
            "attachments_text": "\n\n".join(attachments_text_parts)
        }

        if add_article_to_db(full_article_data):
            print("  ✔ Article is new. Added to the database.")
        else:
            print("  - Article already exists in the database. Skipped.")

    finally:
        # 5. Close the tab and switch back
        driver.close()
        driver.switch_to.window(parent_handle)

# ────────────────────────────────────────────────────────────────────────────────
# Main logic
# ────────────────────────────────────────────────────────────────────────────────

def main(url: str, *, headless: bool = True, keep_open: bool = False) -> None:
    # Check if database file exists. If not, ask user to run setup.
    if not Path(DATABASE_FILE).exists():
        print(f"Error: Database file '{DATABASE_FILE}' not found.")
        print("Please run the `database_setup.py` script first.")
        sys.exit(1)

    drv = build_driver(headless)
    try:
        drv.get(url)
        WebDriverWait(drv, WAIT_SECS).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        if "access denied" in drv.title.lower():
            print("‼ Access denied — aborting.")
            return

        click_period(drv, "1D") # Click '1 Day' filter

        page_no = 1
        while True:
            print(f"\n==== SCANNING LIST PAGE {page_no} ====")
            articles_on_page = extract_list_items(drv)
            if not articles_on_page:
                print("No articles found on this page. Stopping.")
                break

            for art in articles_on_page:
                scrape_article(drv, art) # Process each article

            page_no += 1
            if not goto_next_page(drv):
                break

        print("\n✔ Scraping process complete.")
        if keep_open:
            input("Press <Enter> to close browser…")
    finally:
        drv.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python selenium_open_page.py <URL> [--show] [--keep]")
        sys.exit(1)
    target_url = sys.argv[1]
    show_ui = "--show" in sys.argv
    hold_open = "--keep" in sys.argv
    main(target_url, headless=not show_ui, keep_open=hold_open)