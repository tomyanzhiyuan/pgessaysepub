# Paul Graham Essays to EPUB

A command-line tool that scrapes all essays from Paul Graham's website and compiles them into a single, well-organized EPUB file suitable for Kobo e-readers.

## Features

- **Complete scraping**: Downloads all essays from paulgraham.com/articles.html
- **Read/Unread tracking**: Maintains state of which essays you've read
- **Organized TOC**: Separates unread and read essays in the table of contents
- **Date sorting**: Orders essays by publication date (configurable)
- **Clean formatting**: Minimal CSS optimized for e-ink displays
- **Embedded images**: Includes inline images from articles
- **Kobo-optimized**: Generates EPUBs that work perfectly on Kobo devices

## Installation

1. Clone this repository or download the files
2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Build the EPUB

Generate an EPUB containing all Paul Graham essays:

```bash
python pg_to_epub.py build --output pg_essays.epub
```

Options:
- `--output`, `-o`: Output EPUB file path (default: `pg_essays.epub`)
- `--order`: Sort order for essays: `asc` (oldest first) or `desc` (newest first) (default: `desc`)
- `--force-refresh`: Force re-download of all essays, ignoring cache

Example with options:
```bash
python pg_to_epub.py build --output ~/Desktop/pg_essays.epub --order asc
```

### List Essays

View all essays with their read/unread status:

```bash
python pg_to_epub.py list
```

Options:
- `--unread-only`: Show only unread essays
- `--read-only`: Show only read essays

### Mark Essays as Read

Mark one or more essays as read:

```bash
python pg_to_epub.py mark-read --id avg.html worked.html
```

Or mark by title (partial match):
```bash
python pg_to_epub.py mark-read --title "Beating the Averages" "How to Do Great Work"
```

### Mark Essays as Unread

Mark essays as unread to revisit them:

```bash
python pg_to_epub.py mark-unread --id avg.html
```

### Reset All State

Clear all read/unread state:

```bash
python pg_to_epub.py reset
```

## How It Works

1. **Scraping**: The tool fetches the articles index page, extracts all essay links and metadata
2. **Content Extraction**: Each essay is downloaded and cleaned to extract just the article content
3. **State Management**: Read/unread status is stored in `state.json` in your project directory
4. **EPUB Generation**: All essays are compiled into a single EPUB with:
   - Two main sections: "Unread Essays" and "Read Essays"
   - Each chapter title prefixed with `[UNREAD]` or `[READ]`
   - Essays sorted by publication date within each section
   - Clean, readable CSS optimized for e-ink displays

## Project Structure

```
pgessaysepub/
├── pg_epub/
│   ├── __init__.py
│   ├── config.py         # Configuration constants
│   ├── state.py          # Read/unread state management
│   ├── scraper.py        # Essay list and content fetching
│   ├── parser.py         # HTML content extraction and cleaning
│   └── epub_builder.py   # EPUB file generation
├── pg_to_epub.py         # CLI entrypoint
├── requirements.txt
├── pyproject.toml
└── README.md
```

## State File

The tool maintains a `state.json` file that tracks:
- Which essays you've read
- Cached essay metadata (to avoid re-scraping)
- Last update timestamp

This file is automatically created on first run and updated as you use the tool.

## Workflow

Typical usage pattern (a few times per year):

1. Run `python pg_to_epub.py build` to generate the latest EPUB
2. Copy the EPUB to your Kobo via USB
3. Read essays on your Kobo
4. When you want to update, mark essays as read:
   ```bash
   python pg_to_epub.py mark-read --title "Essay Name"
   ```
5. Regenerate the EPUB with updated read/unread sections
6. Replace the old EPUB on your Kobo

## Requirements

- Python 3.11 or higher
- macOS (should work on Linux/Windows with minor adjustments)
- Internet connection for scraping

## Troubleshooting

**Problem**: Some images aren't appearing in the EPUB
- **Solution**: The tool only includes images that are embedded in essay content. External/decorative images are excluded by design.

**Problem**: Essay dates are missing or incorrect
- **Solution**: Some essays may not have dates. The tool attempts to extract dates from multiple sources but falls back to "Unknown date" if unavailable.

**Problem**: EPUB doesn't open on Kobo
- **Solution**: Ensure you're using a recent version of Kobo firmware. Try opening the EPUB on your computer first with Calibre to verify it's valid.

## License

MIT License - Feel free to modify and use as needed.

## Credits

All essay content © Paul Graham
Tool created for personal educational use
