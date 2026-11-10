# Generic PDF Table Organizer

A Windows Python helper that can download PDFs from a paginated HTML table and sort them into folders by year. It is intended for a user who is already authorized to access a website and signs in manually in the browser.

## Important limitation

There is no reliable way for one URL alone to automate every website: sites use different page structures, custom buttons, embedded applications, and pagination. This tool is a **best-effort generic helper** for ordinary HTML tables with dated rows and document links/buttons. It may not work on sites whose controls are custom or whose table is not exposed as standard HTML. It does not bypass login, CAPTCHA, MFA, or access restrictions.

## Requirements

- Windows 10 or 11
- Python 3.10+
- Google Chrome

## Setup and run

Open Command Prompt in the downloaded project folder and run:

```bat
py -m pip install -r requirements.txt
py generic_pdf_organizer.py
```

Or double-click `run_organizer.bat`.

The program asks for the URL of the document-listing page. It opens a dedicated Chrome profile. Sign in manually in that Chrome window if required, navigate to the listing table, then return to the terminal and press Enter. Signing into a different, already-open Chrome window will not authenticate this dedicated profile.

In the automation profile, disable Chrome's **Settings → Downloads → Ask where to save each file before downloading** option if Chrome shows a save dialog.

## Output

Completed PDFs are moved from the Windows Downloads folder to:

```text
Desktop\PDF Archive\<YEAR>\<YEAR>-<MONTH>_<original-filename>.pdf
```

The script downloads sequentially and stops safely if it cannot identify dated rows, a document action, a completed PDF, or a recognizable next-page control. Review its console messages and test with a small listing first.

## What the helper detects

- Standard HTML tables in open tabs and nested frames
- Italian or English month names, and common numeric month/year date formats
- Links, buttons, and images in a dated row, preferring controls labeled as PDF/document/download
- Common next-page labels such as `Next`, `Avanti`, `Successiva`, `>` and `»`

These heuristics cannot cover every website. Do not use it to download material you are not authorized to access. Never put passwords, session URLs, or tokens in the source code or public repository.

## License

MIT. See [LICENSE](LICENSE).
