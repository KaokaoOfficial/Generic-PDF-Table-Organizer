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
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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


def parse_date(text: str):
    year = re.search(r"\b(?:19|20)\d{2}\b", text)
    if not year:
        return None
    low = text.casefold()
    for month, number in MONTHS.items():
        if month in low:
            return year.group(), number
    return None


def locate_table(driver, timeout=300):
    """Poll every open browser tab and recursively inspect iframes."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for handle in list(driver.window_handles):
            try:
                driver.switch_to.window(handle)
                driver.switch_to.default_content()
                path = _search_frames(driver, ())
                if path is not None:
                    driver.switch_to.default_content()
                    for frame_index in path:
                        driver.switch_to.frame(frame_index)
                    return handle
            except WebDriverException:
                continue
        time.sleep(1)
    return None


def _search_frames(driver, path):
    """Search current frame and descendants; caller switches into path on success."""
    try:
        for table in driver.find_elements(By.TAG_NAME, "table"):
            for row in table.find_elements(By.TAG_NAME, "tr"):
                try:
                    if parse_date(row.text):
                        return path
                except StaleElementReferenceException:
                    continue
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for i in range(len(frames)):
            try:
                driver.switch_to.default_content()
                for parent in path:
                    driver.switch_to.frame(parent)
                frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                driver.switch_to.frame(frames[i])
                found = _search_frames(driver, path + (i,))
                if found is not None:
                    return found
            except WebDriverException:
                continue
        return None
    finally:
        # Do not leave Selenium trapped in a child frame during recursion.
        pass


def rows_on_current_frame(driver):
    rows = []
    for table in driver.find_elements(By.TAG_NAME, "table"):
        for row in table.find_elements(By.TAG_NAME, "tr"):
            try:
                if row.is_displayed() and parse_date(row.text):
                    rows.append(row)
            except StaleElementReferenceException:
                continue
    return rows


def completed_pdf(before, timeout=DOWNLOAD_TIMEOUT_SECONDS):
    deadline = time.monotonic() + timeout
    last = None
    last_size = -1
    stable = 0
    while time.monotonic() < deadline:
        pdfs = [p for p in DOWNLOADS_DIR.glob("*.pdf") if p.name not in before and p.is_file()]
        pdf = max(pdfs, key=lambda p: p.stat().st_mtime, default=None)
        partial = any(DOWNLOADS_DIR.glob("*.crdownload"))
        if pdf:
            size = pdf.stat().st_size
            if pdf == last and size == last_size and not partial:
                stable += 1
                if stable >= 3:
                    return pdf
            else:
                last, last_size, stable = pdf, size, 0
        time.sleep(.5)
    return None


def archive(pdf, year, month):
    target_dir = DEST_ROOT / year
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{year}-{month}_{pdf.name}"
    n = 1
    while target.exists():
        target = target_dir / f"{year}-{month}_{n}_{pdf.name}"
        n += 1
    shutil.move(str(pdf), str(target))
    return target


def click_document(row):
    """On the shown NoiPA grid the document is the fourth cell (index 3)."""
    cells = row.find_elements(By.TAG_NAME, "td")
    if len(cells) < 4:
        return False
    cell = cells[3]
    controls = cell.find_elements(By.CSS_SELECTOR, "a, button, input, img")
    target = controls[0] if controls else cell
    try:
        target.click()
    except WebDriverException:
        row.parent  # keep row reference alive for the JavaScript click below
        row._parent.execute_script("arguments[0].click();", target)
    return True


def find_next(driver):
    for link in driver.find_elements(By.XPATH, "//a[contains(translate(normalize-space(.), 'AVANTI', 'avanti'), 'avanti')]"):
        try:
            if link.is_displayed() and link.get_attribute("aria-disabled") != "true" and "disabled" not in (link.get_attribute("class") or "").casefold():
                return link
        except StaleElementReferenceException:
            continue
    return None


def main():
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
        print("Sign in and open the cartellino table in this automation Chrome window.")
        input("When the table is visible, return here and press Enter: ")
        print("Checking every open tab/frame for the month/year table...")
        table_tab = locate_table(driver)
        if table_tab is None:
            print("No table found within five minutes. Keep it visible in this Chrome window and retry.")
            return

        previous_signature = None
        for page in range(1, MAX_PAGES + 1):
            # locate_table switches to the correct tab and frame each time.
            table_tab = locate_table(driver, timeout=10)
            if table_tab is None:
                print("Could not find the table again; stopping safely.")
                break
            rows = rows_on_current_frame(driver)
            signature = "|".join(r.text.strip() for r in rows)
            if not signature or signature == previous_signature:
                print("No new page rows found; stopping safely.")
                break
            print(f"\n--- Page {page}: found {len(rows)} row(s) ---")

            for index in range(len(rows)):
                # Refresh frame/tab and rows before each interaction; Selenium row
                # references become stale after the site opens a document.
                table_tab = locate_table(driver, timeout=10)
                if table_tab is None:
                    print("Table disappeared; stopping.")
                    return
                rows = rows_on_current_frame(driver)
                if index >= len(rows):
                    break
                row = rows[index]
                text = row.text.strip()
                date = parse_date(text)
                if not date:
                    continue
                before = {p.name for p in DOWNLOADS_DIR.glob("*.pdf")}
                try:
                    if not click_document(row):
                        print(f"No document cell for: {text}")
                        continue
                except WebDriverException as error:
                    print(f"Could not click document for {text}: {error}")
                    continue
                print(f"Waiting for download: {text}")
                pdf = completed_pdf(before)
                if pdf:
                    print(f"Saved: {archive(pdf, *date)}")
                else:
                    print(f"No PDF download detected for: {text}; stopping to avoid misfiling.")
                    return

            previous_signature = signature
            # Find and click next in the current table frame.
            next_link = find_next(driver)
            if not next_link:
                print("No enabled 'avanti' link found; finished.")
                break
            try:
                next_link.click()
            except WebDriverException as error:
                print(f"Could not advance to the next page: {error}")
                break
            time.sleep(2)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
