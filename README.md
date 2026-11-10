# NoiPA PDF Organizer

A small Python/Selenium helper for downloading your own NoiPA cartellino PDFs one at a time and organizing them into year-based folders on Windows.

Example destination:

```text
Desktop\NoiPA\2016\2016-09_03_HR01_01_2016_09_75469_....pdf
```

The script does not ask for or store your password. You sign in manually in the browser it opens. It does not bypass authentication, CAPTCHA, or other access controls.

> **Privacy:** NoiPA documents contain personal information. Keep the downloaded files private and do not commit or upload them to this repository.

## Requirements

- Windows 10/11
- Python 3.10 or later
- Google Chrome
- A NoiPA account authorized to access the documents

## Setup

1. Download or clone this repository.
2. Open Command Prompt in the project folder.
3. Install the dependency:

   ```bat
   py -m pip install -r requirements.txt
   ```

4. Open `noipa_organizer.py` in Notepad and set `NOIPA_URL` to the NoiPA page where you start. Do not paste a URL containing a password, token, or other secret.
5. Save the file.

Chrome will use a separate profile at `%LOCALAPPDATA%\NoiPAChromeProfile`. This avoids interfering with an already-running Chrome profile. The first time, sign in to NoiPA manually in the automation window, navigate to the cartellino table, then return to the Command Prompt and press Enter.

In that Chrome profile, make sure **Settings → Downloads → Ask where to save each file before downloading** is disabled. The script also configures automatic downloads to your Windows Downloads folder.

## Run

From Command Prompt in the project folder:

```bat
py noipa_organizer.py
```

Or double-click `run_noipa.bat`.

The script processes the visible table page, clicks the document cell for each row containing an Italian month and year, waits for the PDF download to finish, and moves it to `Desktop\NoiPA\<YEAR>`. It then follows the table's **avanti** link to continue. Review the console output as it runs.

## Configuration

At the top of `noipa_organizer.py`:

- `NOIPA_URL`: starting page URL (set this yourself; do not share session URLs).
- `DEST_ROOT`: output root, by default `Desktop\NoiPA`.
- `DOWNLOADS_DIR`: temporary Chrome download folder, by default your Windows Downloads folder.
- `MAX_PAGES`: safety limit for pagination.

The program uses a dedicated Chrome profile; it does not attach to an already-open Chrome window. Log in once in the automation window. The profile normally remembers the session, but NoiPA may ask you to authenticate again later.

## Troubleshooting

- **It says no table is available:** make sure you have logged in and opened the cartellino page before pressing Enter.
- **A document is not clicked:** NoiPA may have changed its page markup. Stop the script and report the row/document HTML (remove personal data first) so the selector can be adjusted.
- **A save dialog appears:** disable Chrome's “Ask where to save each file before downloading” setting in the automation profile, then restart the script.
- **Chrome cannot start:** close any other Chrome process using the dedicated `NoiPAChromeProfile` directory and try again.
- **It does not advance pages:** pagination controls may have changed; the script intentionally stops rather than guessing and repeatedly downloading the same page.

Test with a small number of documents first and verify the resulting files and year folders before processing the full archive. Use the script only in accordance with NoiPA's terms and your organization's policies.

## License

MIT. See [LICENSE](LICENSE).
