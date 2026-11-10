"""Download NoiPA cartellino PDFs sequentially and sort them by year.

Uses a dedicated Chrome profile. The user signs in and navigates to the
cartellino table manually; credentials and session URLs are not stored.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    NoSuchFrameException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Start at the public portal home page. Do not put a session-specific URL,
# STARTKEY, password, or other temporary token in this file.
NOIPA_URL = "https://noipa.mef.gov.it/"
DEST_ROOT = Path.home() / "Desktop" / "NoiPA"
DOWNLOADS_DIR = Path.home() / "Downloads"
CHROME_PROFILE_DIR = Path.home() / "AppData" / "Local" / "NoiPAChromeProfile"
MAX_PAGES = 50
DOWNLOAD_TIMEOUT_SECONDS = 60

MONTHS = {
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
}


def parse_year_month(text: str) -> tuple[str, str] | None:
    year_match = re.search(r"\b(?:19|20)\d{2}\b", text)
    if not year_match:
        return None
    lowered = text.casefold()
    for name, number in MONTHS.items():
        if name in lowered:
            return year_match.group(), number
    return None


def _find_table_frame_path(driver: webdriver.Chrome) -> tuple[int, ...] | None:
    """Find a document table in the main page or a nested iframe."""
    def walk(path: tuple[int, ...]) -> tuple[int, ...] | None:
        try:
            driver.switch_to.default_content()
            for frame_index in path:
                driver.switch_to.frame(frame_index)

            for table in driver.find_elements(By.TAG_NAME, "table"):
                for row in table.find_elements(By.TAG_NAME, "tr"):
                    try:
                        if parse_year_month(row.text):
                            return path
                    except StaleElementReferenceException:
                        continue

            frame_count = len(driver.find_elements(By.CSS_SELECTOR, "iframe, frame"))
            for index in range(frame_count):
                try:
                    driver.switch_to.default_content()
                    for frame_index in path:
                        driver.switch_to.frame(frame_index)
                    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                    if index >= len(frames):
                        continue
                    driver.switch_to.frame(frames[index])
                    found = walk(path + (index,))
                    if found is not None:
                        return found
                except (NoSuchFrameException, StaleElementReferenceException, WebDriverException):
                    continue
            return None
        except (NoSuchFrameException, StaleElementReferenceException, WebDriverException):
            return None
        finally:
            driver.switch_to.default_content()

    return walk(())


def _switch_to_table(driver: webdriver.Chrome) -> bool:
    path = _find_table_frame_path(driver)
    if path is None:
        driver.switch_to.default_content()
        return False
    driver.switch_to.default_content()
    try:
        for frame_index in path:
            driver.switch_to.frame(frame_index)
        return True
    except (NoSuchFrameException, WebDriverException):
        driver.switch_to.default_content()
        return False


def wait_for_table(driver: webdriver.Chrome, timeout: int = 300) -> bool:
    """Wait for the user to reach the table, including tables inside frames."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _find_table_frame_path(driver) is not None:
            return True
        time.sleep(1)
    return False


def get_document_rows(driver: webdriver.Chrome):
    if not _switch_to_table(driver):
        return []
    rows = []
    try:
        for table in driver.find_elements(By.TAG_NAME, "table"):
            for row in table.find_elements(By.TAG_NAME, "tr"):
                try:
                    if row.is_displayed() and parse_year_month(row.text):
                        rows.append(row)
                except StaleElementReferenceException:
                    continue
    finally:
        driver.switch_to.default_content()
    return rows


def wait_for_pdf(before: set[str], timeout: int = DOWNLOAD_TIMEOUT_SECONDS) -> Path | None:
    deadline = time.monotonic() + timeout
    last_path: Path | None = None
    last_size = -1
    stable_checks = 0
    while time.monotonic() < deadline:
        candidates = [p for p in DOWNLOADS_DIR.glob("*.pdf") if p.name not in before and p.is_file()]
        candidate = max(candidates, key=lambda p: p.stat().st_mtime, default=None)
        partial = any(DOWNLOADS_DIR.glob("*.crdownload"))
        if candidate:
            size = candidate.stat().st_size
            if candidate == last_path and size == last_size and not partial:
                stable_checks += 1
                if stable_checks >= 3:
                    return candidate
            else:
                last_path, last_size, stable_checks = candidate, size, 0
        time.sleep(0.5)
    return None


def save_pdf(pdf: Path, year: str, month: str) -> Path:
    folder = DEST_ROOT / year
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{year}-{month}_{pdf.name}"
    counter = 1
    while destination.exists():
        destination = folder / f"{year}-{month}_{counter}_{pdf.name}"
        counter += 1
    shutil.move(str(pdf), str(destination))
    return destination


def download_row(driver: webdriver.Chrome, row_index: int) -> None:
    rows = get_document_rows(driver)
    if row_index >= len(rows):
        return
    row_text = rows[row_index].text.strip()
    date = parse_year_month(row_text)
    if not date or not _switch_to_table(driver):
        return

    try:
        # Reacquire the row after switching into the correct frame context.
        rows_in_context = []
        for table in driver.find_elements(By.TAG_NAME, "table"):
            for row in table.find_elements(By.TAG_NAME, "tr"):
                try:
                    if row.is_displayed() and parse_year_month(row.text):
                        rows_in_context.append(row)
                except StaleElementReferenceException:
                    pass
        if row_index >= len(rows_in_context):
            return
        cells = rows_in_context[row_index].find_elements(By.TAG_NAME, "td")
        if len(cells) < 4:
            print(f"Document cell not found: {row_text}")
            return
        document_cell = cells[3]
        before = {p.name for p in DOWNLOADS_DIR.glob("*.pdf")}
        controls = document_cell.find_elements(By.CSS_SELECTOR, "a, button, input, img")
        try:
            (controls[0] if controls else document_cell).click()
        except WebDriverException:
            driver.execute_script("arguments[0].click();", controls[0] if controls else document_cell)
    finally:
        driver.switch_to.default_content()

    print(f"Downloading: {row_text}")
    pdf = wait_for_pdf(before)
    if pdf:
        year, month = date
        print(f"Saved: {save_pdf(pdf, year, month)}")
    else:
        print(f"No completed PDF detected for: {row_text}")

    # A document may open in a separate tab; close only the extra tab.
    handles = driver.window_handles
    if len(handles) > 1:
        main_handle = handles[0]
        for handle in handles[1:]:
            driver.switch_to.window(handle)
            driver.close()
        driver.switch_to.window(main_handle)


def page_signature(driver: webdriver.Chrome) -> str:
    return "|".join(row.text.strip() for row in get_document_rows(driver))


def click_next_page(driver: webdriver.Chrome) -> bool:
    if not _switch_to_table(driver):
        return False
    try:
        links = driver.find_elements(
            By.XPATH,
            "//a[contains(translate(normalize-space(.), 'AVANTI', 'avanti'), 'avanti')]"
        )
        for link in links:
            try:
                if link.is_displayed() and link.get_attribute("aria-disabled") != "true":
                    if "disabled" not in (link.get_attribute("class") or "").casefold():
                        link.click()
                        time.sleep(2)
                        return True
            except (StaleElementReferenceException, WebDriverException):
                continue
        return False
    finally:
        driver.switch_to.default_content()


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
        print("Chrome uses a separate profile. Sign in there, open the cartellino table,")
        input("then return here and press Enter. The script will search the page and its frames: ")
        print("Looking for the table in the page and embedded frames (up to 5 minutes)...")
        if not wait_for_table(driver):
            print("No month/year document table detected. Leave the cartellino table visible and retry.")
            return

        previous_signature = None
        for page_number in range(1, MAX_PAGES + 1):
            signature = page_signature(driver)
            if not signature:
                print("No month/year rows detected; stopping without downloading.")
                break
            if signature == previous_signature:
                print("The page did not change; stopping to avoid duplicates.")
                break
            print(f"\n--- Page {page_number}: {len(signature.split('|'))} document row(s) ---")
            row_count = len(signature.split("|"))
            for index in range(row_count):
                download_row(driver, index)
            previous_signature = signature
            if not click_next_page(driver):
                print("No enabled 'avanti' link found; finished.")
                break
        else:
            print(f"Reached the safety limit of {MAX_PAGES} pages.")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
