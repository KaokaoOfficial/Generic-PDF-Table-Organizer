# Generic PDF Table Organizer

A Windows Python helper that attempts to download PDF documents from a paginated HTML table and organize them into folders by year. It is designed for people who are authorized to access the website and can sign in manually in the browser.

## Important: what this program can and cannot do

This is a best-effort browser automation tool, not a universal downloader. It works best when the listing page contains a standard HTML table with:

- rows that show a recognizable date, month, and year;
- a visible link, button, or icon in each document row that opens or downloads a PDF;
- pagination with a recognizable control such as `Next`, `Avanti`, or `Successiva`.

The program can look through open browser tabs and embedded frames, but websites differ. A custom web application, unusual date format, inaccessible table, or differently labeled control may require code changes. It does not bypass login, multi-factor authentication, CAPTCHA, or access restrictions.

## Requirements

- Windows 10 or 11
- Python 3.10 or later
- Google Chrome
- Permission to view and download the documents from the target website

## Download the project

On the repository page, choose **Code → Download ZIP**, then extract the ZIP to a normal folder, for example:

```text
Documents\Generic-PDF-Table-Organizer\
```

Alternatively, clone the repository with Git. Do not put downloaded personal documents into the source repository.

## Install and start

Open Command Prompt in the extracted project folder. One way is to open that folder in File Explorer, click the address bar, type `cmd`, and press Enter. Then run:

```bat
py -m pip install -r requirements.txt
py generic_pdf_organizer.py
```

You can also double-click `run_organizer.bat`; it installs the dependency and starts the script.

## Where to enter the website URL

When the program starts, the Command Prompt displays:

```text
Enter the URL of the document listing page:
```

Paste the URL into that terminal prompt and press Enter. **Do not paste the URL into the Python source code or README.** Use the address of the page that contains the document list, if possible. The URL must begin with `http://` or `https://`.

If the listing URL contains a temporary session key, access token, or other private value, do not post it publicly or save it in the repository. You can enter the website's safe starting address instead, sign in in the browser, and navigate to the listing page manually.

## Sign in and begin

1. The script opens a separate, dedicated Chrome profile. It does not use or take over your regular Chrome profile.
2. If the site requires authentication, sign in manually in this automation Chrome window. Never put your password in the script.
3. Navigate in that same window to the page with the document table. Signing in or opening the table in a different Chrome window will not transfer that session.
4. Return to Command Prompt and wait for the prompt:

   ```text
   Once the listing table is visible, press Enter here:
   ```

5. Press Enter. The script searches open tabs and embedded frames for a table with dated rows, then processes the rows sequentially.

Chrome is configured to download PDFs into your Windows **Downloads** folder without asking for a save location. If Chrome still displays a save dialog, disable **Settings → Downloads → Ask where to save each file before downloading** in the automation profile and restart the script.

## What happens during a run

For each page, the program:

1. Looks for table rows containing a month/year or a supported numeric date.
2. Tries to identify a visible PDF/document/download control in each dated row.
3. Clicks one row's control and waits for a new completed PDF in Downloads before moving on.
4. Creates a year folder and moves the PDF into it with a year/month prefix.
5. Looks for a common next-page control and repeats, up to a safety limit of 100 pages.

The program prints progress and errors in the Command Prompt. It stops rather than guessing if it cannot find a supported table, document action, completed PDF, or next-page control. Review the messages and verify the saved files, especially on the first run. Start with a small listing or stop after a few downloads to test that the correct document is associated with each date.

## Where files are saved

By default, PDFs are moved out of Downloads into:

```text
Desktop\PDF Archive\<YEAR>\<YEAR>-<MONTH>_<original-filename>.pdf
```

For example:

```text
Desktop\PDF Archive\2026\2026-09_monthly-report.pdf
```

The output folder and other settings can be changed near the top of `generic_pdf_organizer.py` (`DEST_ROOT`, `DOWNLOADS_DIR`, `MAX_PAGES`, and `DOWNLOAD_TIMEOUT`). Do not change the browser profile path while the program is running.

## Stop the program

To stop a run, focus the Command Prompt window and press **Ctrl+C**. The browser will close when the script exits. Do not close the browser while a PDF is downloading unless you also intend to stop the run.

## Troubleshooting

- **The browser opens but no table is found:** confirm you signed in and the document table is visible in the automation Chrome window before pressing Enter. The listing may not be a standard HTML table.
- **It finds rows but skips them:** the date format or document control may not match the program's heuristics.
- **It clicks but detects no PDF:** check Chrome's download setting and confirm a PDF appears in Downloads when you click one document manually.
- **It does not move to another page:** the site's pagination control may use a label or behavior the generic helper does not recognize.
- **Chrome fails to start:** close another Chrome process using the dedicated profile, then retry. Do not point Selenium at your personal Chrome profile.

If it still fails, share the exact terminal output and a screenshot with names, document data, private URLs, session keys, and tokens hidden. Never share passwords, session URLs, access tokens, or downloaded personal documents.

## Privacy and authorized use

Use this program only for documents you are authorized to access and in accordance with the website's terms and your organization's policies. The browser session is handled manually; the script does not store credentials or attempt to bypass access controls. Keep the downloaded PDFs private.

## License

MIT. See [LICENSE](LICENSE).
