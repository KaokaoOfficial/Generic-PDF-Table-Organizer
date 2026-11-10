"""Download PDF documents from a paginated HTML table and organize them by year.

This is a best-effort generic browser helper, not a universal scraper. It works
with ordinary HTML tables whose rows contain a recognizable month/year and a
document link/button. The user signs in manually in a dedicated Chrome profile.
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

DEST_ROOT = Path.home() / "Desktop" / "PDF Archive"
DOWNLOADS_DIR = Path.home() / "Downloads"
PROFILE_DIR = Path.home() / "AppData" / "Local" / "PDFArchiveChromeProfile"
MAX_PAGES = 100
DOWNLOAD_TIMEOUT = 90
MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
}


def parse_year_month(text: str):
    """Find a year plus a month name or numeric month in row text."""
    year_match = re.search(r"\b(?:19|20)\d{2}\b", text)
    if not year_match:
        return None
    low = text.casefold()
    for name, number in MONTHS.items():
        if re.search(rf"\b{re.escape(name)}\b", low):
            return year_match.group(), number
    # Common numeric dates: YYYY-MM[-DD], DD/MM/YYYY, MM/YYYY.
    y, m = year_match.group(), None
    iso = re.search(rf"\b{y}[-/.](0?[1-9]|1[0-2])(?:[-/.]\d{{1,2}})?\b", text)
    dmy = re.search(rf"\b\d{{1,2}}[-/.](0?[1-9]|1[0-2])[-/.]{y}\b", text)
    my = re.search(rf"\b(0?[1-9]|1[0-2])[-/.]{y}\b", text)
    match = iso or dmy or my
    if match:
        m = next((g for g in match.groups() if g and g.isdigit() and 1 <= int(g) <= 12), None)
    if m:
        return y, f"{int(m):02d}"
    return None


def find_table_path(driver):
    """Search open tabs and nested frames for a table with dated rows and actions."""
    for handle in list(driver.window_handles):
        try:
            driver.switch_to.window(handle)
            driver.switch_to.default_content()
            path = _search_frame(driver, ())
            if path is not None:
                driver.switch_to.default_content()
                for index in path:
                    driver.switch_to.frame(index)
                return handle
        except WebDriverException:
            continue
    driver.switch_to.default_content()
    return None


def _search_frame(driver, path):
    try:
        for table in driver.find_elements(By.TAG_NAME, "table"):
            for row in table.find_elements(By.TAG_NAME, "tr"):
                try:
                    if parse_year_month(row.text) and row.find_elements(By.CSS_SELECTOR, "a, button, input, img"):
                        return path
                except StaleElementReferenceException:
                    continue
        driver.switch_to.default_content()
        for parent in path:
            driver.switch_to.frame(parent)
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        for i in range(len(frames)):
            try:
                driver.switch_to.default_content()
                for parent in path:
                    driver.switch_to.frame(parent)
                frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                driver.switch_to.frame(frames[i])
                result = _search_frame(driver, path + (i,))
                if result is not None:
                    return result
            except WebDriverException:
                continue
        return None
    except WebDriverException:
        return None


def rows_here(driver):
    result = []
    for table in driver.find_elements(By.TAG_NAME, "table"):
        for row in table.find_elements(By.TAG_NAME, "tr"):
            try:
                if row.is_displayed() and parse_year_month(row.text):
                    result.append(row)
            except StaleElementReferenceException:
                pass
    return result


def find_document_action(row):
    """Prefer PDF/document/download links; otherwise pick an action in the row."""
    actions = row.find_elements(By.CSS_SELECTOR, "a, button, input, img")
    scored = []
    for action in actions:
        try:
            info = " ".join((action.text or "", action.get_attribute("title") or "",
                             action.get_attribute("aria-label") or "",
                             action.get_attribute("href") or "",
                             action.get_attribute("alt") or "")).casefold()
            score = 0
            if ".pdf" in info or "pdf" in info:
                score += 5
            if any(word in info for word in ("document", "download", "file", "scarica", "documento")):
                score += 3
            if action.is_displayed():
                scored.append((score, action))
        except StaleElementReferenceException:
            continue
    if not scored:
        return None
    # If multiple candidates are present but none identifies a document, don't
    # guess; this avoids clicking unrelated row actions.
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == 0:
        return None
    return scored[0][1]


def wait_download(before):
    end = time.monotonic() + DOWNLOAD_TIMEOUT
    previous_path, previous_size, stable = None, -1, 0
    while time.monotonic() < end:
        candidates = [p for p in DOWNLOADS_DIR.glob("*.pdf") if p.name not in before and p.is_file()]
        pdf = max(candidates, key=lambda p: p.stat().st_mtime, default=None)
        if pdf and not any(DOWNLOADS_DIR.glob("*.crdownload")):
            size = pdf.stat().st_size
            if pdf == previous_path and size == previous_size:
                stable += 1
                if stable >= 3:
                    return pdf
            else:
                previous_path, previous_size, stable = pdf, size, 0
        time.sleep(.5)
    return None


def archive(pdf, year, month):
    folder = DEST_ROOT / year
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{year}-{month}_{pdf.name}"
    n = 1
    while target.exists():
        target = folder / f"{year}-{month}_{n}_{pdf.name}"
        n += 1
    shutil.move(str(pdf), str(target))
    return target


def click_next(driver):
    candidates = driver.find_elements(By.XPATH, "//a | //button")
    for element in candidates:
        try:
            label = " ".join((element.text or "", element.get_attribute("title") or "",
                              element.get_attribute("aria-label") or "")).casefold().strip()
            if label in {"next", "next page", "avanti", "successiva", ">", "›", "»"}:
                if element.is_displayed() and element.get_attribute("aria-disabled") != "true":
                    if "disabled" not in (element.get_attribute("class") or "").casefold():
                        element.click()
                        time.sleep(2)
                        return True
        except WebDriverException:
            continue
    return False


def main():
    url = input("Enter the URL of the document listing page: ").strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print("Please enter a valid http:// or https:// page URL.")
        return
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_experimental_option("prefs", {
        "download.default_directory": str(DOWNLOADS_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        print("Sign in manually in this dedicated Chrome window if needed.")
        print("Navigate to the listing table, then return to this terminal.")
        input("Press Enter when the document listing is visible: ")
        previous_signature = None
        for page in range(1, MAX_PAGES + 1):
            table_tab = find_table_path(driver)
            if table_tab is None:
                print("No supported HTML table found in open tabs/frames. Stopping safely.")
                break
            rows = rows_here(driver)
            signature = "|".join(row.text.strip() for row in rows)
            if not rows or signature == previous_signature:
                print("No new dated rows found; stopping safely.")
                break
            print(f"\nPage {page}: found {len(rows)} dated row(s).")
            for i in range(len(rows)):
                if find_table_path(driver) is None:
                    print("Table disappeared; stopping.")
                    return
                current_rows = rows_here(driver)
                if i >= len(current_rows):
                    break
                row = current_rows[i]
                date = parse_year_month(row.text)
                action = find_document_action(row)
                if not date or action is None:
                    print(f"Skipped row (date/action unclear): {row.text.strip()}")
                    continue
                before = {p.name for p in DOWNLOADS_DIR.glob("*.pdf")}
                try:
                    action.click()
                except WebDriverException as error:
                    print(f"Could not click row action: {error}")
                    continue
                print(f"Waiting for PDF: {row.text.strip()}")
                pdf = wait_download(before)
                if not pdf:
                    print("No completed PDF detected. Stopping to avoid misfiling.")
                    return
                print(f"Saved: {archive(pdf, *date)}")
            previous_signature = signature
            if not click_next(driver):
                print("No recognizable next-page control; finished current page.")
                break
        else:
            print(f"Reached safety limit ({MAX_PAGES} pages).")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
