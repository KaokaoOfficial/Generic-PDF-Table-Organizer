# NoiPA PDF Organizer

A small Python/Selenium helper for downloading your own NoiPA cartellino PDFs one at a time and organizing them into year-based folders on Windows.

> **Privacy and security:** the script uses a separate Chrome profile and requires you to sign in manually. Do not publish or commit a full NoiPA URL containing temporary parameters such as `STARTKEY`, and never share passwords, session links, or downloaded documents. The script does not bypass authentication or access controls.

## Requirements

- Windows 10/11, Python 3.10+, and Google Chrome
- A NoiPA account authorized to access the documents

## Setup

1. Download/clone this repository and open Command Prompt in its folder.
2. Install Selenium:

   ```bat
   py -m pip install -r requirements.txt
   ```

3. Run the program:

   ```bat
   py noipa_organizer.py
   ```

   Or double-click `run_noipa.bat`.
4. In the Chrome window opened by the script, sign in manually and navigate to the cartellino page showing the month/year document table. This is a separate profile from your normal Chrome window; signing in to another Chrome window does not sign in here.
5. Return to the Command Prompt and press Enter. The script checks the main page and embedded frames for rows containing an Italian month and year.

Chrome is configured to download PDFs automatically to the Windows Downloads folder. If a save dialog still appears, disable **Chrome Settings → Downloads → Ask where to save each file before downloading** in the automation profile.

## Output

Files are moved to `Desktop\NoiPA\<YEAR>\` and prefixed with the row month and year, for example:

```text
Desktop\NoiPA\2016\2016-09_original-name.pdf
```

The script downloads sequentially, then follows a visible `avanti` pagination link. Test a few documents first and review the console and output before processing the full archive.

## Important configuration

`NOIPA_URL` defaults to the public portal home page. Do not put a personal or temporary URL (including a URL with `STARTKEY` or other session parameters) in this public repository. Navigate to the cartellino page manually in the browser opened by the script.

Output and profile paths can be changed near the top of `noipa_organizer.py`. The dedicated profile is stored under `%LOCALAPPDATA%\NoiPAChromeProfile`.

## Troubleshooting

- **No month/year table detected:** confirm the cartellino table is visible in the automation Chrome window before pressing Enter. The script searches embedded frames too; if it still fails, stop and share only the terminal error (not a session URL or personal PDF).
- **A document is not detected/downloaded:** NoiPA may have changed its page layout. Stop the run and review the table markup before retrying.
- **Chrome cannot start:** close Chrome processes using the dedicated `NoiPAChromeProfile` and retry.

Use this tool only for documents you are authorized to access and in accordance with NoiPA's terms and your organization's policies.

## License

MIT. See [LICENSE](LICENSE).
