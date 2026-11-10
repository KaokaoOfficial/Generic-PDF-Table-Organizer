"""Download NoiPA cartellino PDFs sequentially and sort them by year.

This script uses a dedicated Chrome profile and requires the user to sign in
manually. It does not handle credentials or bypass access controls.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (  # type: ignore[import-untyped]
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

# Set this to a safe starting NoiPA page URL. Do not put credentials or
# session tokens in this file. You will sign in manually in the opened browser.
NOIPA_URL = "https://noipa.mef.gov.it/"

DEST_ROOT = Path.home() / "Desktop" / "NoiPA"
DOWNLOADS_DIR = Path.home() / "Downloads"
CHROME_PROFILE_DIR = Path.home() / "AppData" / "Local" / "NoiPAChromeProfile"
MAX_PAGES = 50
DOWNLOAD_TIMEOUT_SECONDS = 60

MONTHS = {
    "gennaio": "01",
    "febbraio": "02",
    "marzo": "03",
    "aprile": "04",
    "maggio": "05",
    "giugno": "06",
    "luglio": "07",
    "agosto": "08",
    "settembre": "09",
    "ottobre": "10",
    "novembre": "11",
    "dicembre": "12",
}


def parse_year_month(text: str) -> tuple[str, str] | None:
    """Return (YYYY, MM) when the row contains an Italian month and year."""
    year_match = re.search(r"\b(?:19|20)\d{2}\b", text)
    if not year_match:
        return None
    lowered = text.casefold()
    for month_name, month_number in MONTHS.items():
        if month_name in lowered:
            return year_match.group(), month_number
    return None


def wait_for_page_table(driver: webdriver.Chrome) -> None:
    """Wait until at least one table row appears after the user logs in."""
    WebDriverWait(driver, 300).until(
        lambda browser: any(
            row.is_displayed()
            for table in browser.find_elements(By.TAG_NAME, "table")
            for row in table.find_elements(By.TAG_NAME, "tr")
        )
    )


def visible_document_rows(driver: webdriver.Chrome):
    """Find visible table rows with a recognizable month/year."""
    found = []
    for table in driver.find_elements(By.TAG_NAME, "table"):
        for row in table.find_elements(By.TAG_NAME, "tr"):
            try:
                if row.is_displayed() and parse_year_month(row.text):
                    found.append(row)
            except StaleElementReferenceException:
                continue
    return found


def click_document_cell(row) -> bool:
    """Click the document-column control, falling back to its table cell."""
    try:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 4:
            return False
        document_cell = cells[3]
        for selector in ("a", "button", "input", "img"):
            controls = document_cell.find_elements(By.CSS_SELECTOR, selector)
            for control in controls:
                try:
                    control.click()
                    return True
                except WebDriverException:
                    continue
        document_cell.click()
        return True
    except (NoSuchElementException, StaleElementReferenceException, WebDriverException):
        return False


def wait_for_pdf(before: set[Path], timeout: int = DOWNLOAD_TIMEOUT_SECONDS) -> Path | None:
    """Wait for a new completed PDF download and allow its size to settle."""
    deadline = time.monotonic() + timeout
    last_candidate: Path | None = None
    stable_checks = 0
    previous_size = -1

    while time.monotonic() < deadline:
        candidates = [
            path for path in DOWNLOADS_DIR.glob("*.pdf")
            if path not in before and path.is_file()
        ]
        candidate = max(candidates, key=lambda path: path.stat().st_mtime, default=None)
        partial_downloads = list(DOWNLOADS_DIR.glob("*.crdownload"))

        if candidate is not None:
            size = candidate.stat().st_size
            if candidate == last_candidate and size == previous_size and not partial_downloads:
                stable_checks += 1
                if stable_checks >= 3:
                    return candidate
            else:
                last_candidate = candidate
                previous_size = size
                stable_checks = 0
        time.sleep(0.5)

    return None


def save_pdf(pdf: Path, year: str, month: str) -> Path:
    """Move a downloaded PDF to Desktop/NoiPA/YYYY with a sortable prefix."""
    year_directory = DEST_ROOT / year
    year_directory.mkdir(parents=True, exist_ok=True)
    destination = year_directory / f"{year}-{month}_{pdf.name}"
    counter = 1
    while destination.exists():
        destination = year_directory / f"{year}-{month}_{counter}_{pdf.name}"
        counter += 1
    shutil.move(str(pdf), str(destination))
    return destination


def click_next_page(driver: webdriver.Chrome) -> bool:
    """Click a visible enabled pagination link labeled 'avanti'."""
    for link in driver.find_elements(By.XPATH, "//a[contains(translate(normalize-space(.), 'AVANTI', 'avanti'), 'avanti')]"):
        try:
            if not link.is_displayed():
                continue
            classes = (link.get_attribute("class") or "").casefold()
            if "disabled" in classes or link.get_attribute("aria-disabled") == "true":
                continue
            link.click()
            time.sleep(1.5)
            return True
        except (StaleElementReferenceException, WebDriverException):
            continue
    return False


def process_current_page(driver: webdriver.Chrome) -> str:
    """Download rows on the current page; return a signature for loop checks."""
    rows = visible_document_rows(driver)
    signature = "|".join(row.text.strip() for row in rows)
    print(f"Found {len(rows)} document row(s) on this page.")

    for index in range(len(rows)):
        try:
            # Reacquire rows because the page may refresh after a document click.
            current_rows = visible_document_rows(driver)
            if index >= len(current_rows):
                break
            row = current_rows[index]
            row_text = row.text.strip()
            date = parse_year_month(row_text)
            if not date:
                continue
            year, month = date
            before = set(DOWNLOADS_DIR.glob("*.pdf"))
            if not click_document_cell(row):
                print(f"Could not click document for row: {row_text}")
                continue

            print(f"Waiting for PDF: {row_text}")
            pdf = wait_for_pdf(before)
            if pdf:
                print(f"Saved: {save_pdf(pdf, year, month)}")
            else:
                print(f"No completed PDF download detected for row: {row_text}")

            # If a PDF opened in a new tab, close it and return to the table.
            handles = driver.window_handles
            if len(handles) > 1:
                main_handle = handles[0]
                for handle in handles[1:]:
                    driver.switch_to.window(handle)
                    driver.close()
                driver.switch_to.window(main_handle)
        except (StaleElementReferenceException, WebDriverException) as error:
            print(f"Skipped a row because the page changed: {error}")

    return signature


def main() -> None:
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_experimental_option("prefs", {
        "download.default_directory": str(DOWNLOADS_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(NOIPA_URL)
        print("Sign in to NoiPA in the Chrome window, open the cartellino table,")
        input("then return here and press Enter to start downloading: ")
        try:
            wait_for_page_table(driver)
        except TimeoutException:
            print("No table appeared within five minutes. Check the browser and try again.")
            return

        previous_signature = None
        for page_number in range(1, MAX_PAGES + 1):
            print(f"\n--- Page {page_number} ---")
            signature = process_current_page(driver)
            if not signature or signature == previous_signature:
                print("Page is empty or unchanged; stopping to avoid duplicate downloads.")
                break
            previous_signature = signature
            if not click_next_page(driver):
                print("No enabled 'avanti' pagination link found; finished.")
                break
        else:
            print(f"Reached the safety limit of {MAX_PAGES} pages.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
