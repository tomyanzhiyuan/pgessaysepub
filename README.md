# Paul Graham Essays to EPUB

[![CI](https://github.com/tomyanzhiyuan/pgessaysepub/actions/workflows/ci.yml/badge.svg)](https://github.com/tomyanzhiyuan/pgessaysepub/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A command-line tool that scrapes all essays from Paul Graham's website and compiles them into a single, well-organized EPUB file optimized for Kobo e-readers.

## 📥 Quick Download

**Just want the EPUB?** Visit **[tomyanzhiyuan.github.io/pgessaysepub](https://tomyanzhiyuan.github.io/pgessaysepub)** to download the latest version with one click.

---

## Features

- **Complete Collection**: Downloads all 230+ essays from paulgraham.com
- **Kobo-Optimized**: Generates clean EPUBs that work perfectly on Kobo devices
- **Date Sorting**: Orders essays by publication date (newest first by default)
- **Custom Cover**: Add your own cover image to the EPUB
- **Smart Caching**: Only re-downloads essays when needed
- **Clean Formatting**: Minimal CSS optimized for e-ink displays
- **Embedded Images**: Includes inline images from articles

## Installation

### From Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/tomyanzhiyuan/pg-essays-epub.git
cd pg-essays-epub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

### Using pip

```bash
pip install pg-essays-epub
```

## Quick Start

Generate an EPUB with all Paul Graham essays:

```bash
# Using the CLI command (after pip install)
pg-essays-epub build --output pg_essays.epub

# Or using Python directly
python pg_to_epub.py build --output pg_essays.epub
```

## Usage

### Build the EPUB

```bash
pg-essays-epub build --output pg_essays.epub --cover cover.png
```

Options:
- `--output`, `-o`: Output EPUB file path (default: `pg_essays.epub`)
- `--cover`: Path to cover image (PNG or JPG)
- `--order`: Sort order: `asc` (oldest first) or `desc` (newest first, default)
- `--force-refresh`: Force re-download of all essays
- `--rebuild`: Use cached content only (fastest, offline)

### List Essays

```bash
pg-essays-epub list              # All essays
pg-essays-epub list --unread-only  # Only unread
```

### Mark Essays as Read/Unread

```bash
# By essay ID
pg-essays-epub mark-read --id avg.html worked.html

# By title (partial match)
pg-essays-epub mark-read --title "Beating the Averages"

# Mark as unread
pg-essays-epub mark-unread --id avg.html
```

### Reset State

```bash
pg-essays-epub reset --confirm
```

## Project Structure

```
pg-essays-epub/
├── pg_epub/
│   ├── config.py         # Configuration constants
│   ├── state.py          # Read/unread state management
│   ├── scraper.py        # Essay fetching
│   ├── parser.py         # HTML content extraction
│   ├── epub_builder.py   # EPUB generation
│   └── cache.py          # Content caching
├── tests/                # Unit tests
├── pg_to_epub.py         # CLI entrypoint
├── pyproject.toml        # Package configuration
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check pg_epub/ pg_to_epub.py

# Format code
black pg_epub/ pg_to_epub.py
```

## Workflow

Typical usage (update every few months):

1. **Build**: `pg-essays-epub build -o essays.epub --cover cover.png`
2. **Transfer**: Copy `essays.epub` to your Kobo via USB
3. **Read**: Enjoy essays on your e-reader
4. **Update**: When new essays are published, rebuild with `--force-refresh`

## Troubleshooting

**EPUB doesn't open on Kobo**
- Ensure Kobo firmware is up to date
- Try validating the EPUB with [EPUBCheck](https://www.w3.org/publishing/epubcheck/)

**Images missing**
- Some external images may fail to download (404 errors are normal)
- The tool only includes images embedded in essay content

**Build is slow**
- First build downloads all essays (~230). Use `--rebuild` for subsequent builds
- Cached content is stored in `.cache/`

## Requirements

- Python 3.11 or higher
- Internet connection (for initial scraping)

## Disclaimer

This is an **unofficial** project for personal and educational use only. All essays are copyrighted by Paul Graham and are freely available at [paulgraham.com](https://paulgraham.com).

This project is not affiliated with, endorsed by, or sponsored by Paul Graham or Y Combinator. If requested by the author, this project will be taken down immediately.

**Please support the original author** by visiting [paulgraham.com](https://paulgraham.com).

## License

MIT License - See [LICENSE](LICENSE) for details.

*Note: The MIT license applies to the code in this repository only, not to the essay content.*
