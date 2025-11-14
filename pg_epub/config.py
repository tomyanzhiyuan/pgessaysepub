"""
Configuration constants and options for the PG Essays EPUB tool.
"""

from pathlib import Path

# URLs
ARTICLES_INDEX_URL = "https://paulgraham.com/articles.html"
BASE_URL = "https://paulgraham.com"

# File paths
PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / "state.json"
CACHE_DIR = PROJECT_ROOT / ".cache"
IMAGES_CACHE_DIR = CACHE_DIR / "images"
CONTENT_CACHE_DIR = CACHE_DIR / "content"

# Ensure cache directories exist
CACHE_DIR.mkdir(exist_ok=True)
IMAGES_CACHE_DIR.mkdir(exist_ok=True)
CONTENT_CACHE_DIR.mkdir(exist_ok=True)

# EPUB metadata
EPUB_TITLE = "Paul Graham Essays (Complete Collection)"
EPUB_AUTHOR = "Paul Graham"
EPUB_LANGUAGE = "en"
EPUB_PUBLISHER = "paulgraham.com"

# HTTP settings
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.5  # Seconds between requests to be polite

# EPUB styling
EPUB_CSS = """
body {
    font-family: serif;
    line-height: 1.6;
    margin: 1em;
    text-align: left;
}

h1 {
    font-size: 1.8em;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
    font-weight: bold;
    text-align: left;
}

h2 {
    font-size: 1.4em;
    margin-top: 0.8em;
    margin-bottom: 0.4em;
    font-weight: bold;
}

p {
    margin: 0.5em 0;
    text-indent: 0;
}

blockquote {
    margin: 1em 2em;
    font-style: italic;
}

ul, ol {
    margin: 0.5em 0;
    padding-left: 2em;
}

li {
    margin: 0.3em 0;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

a {
    color: inherit;
    text-decoration: underline;
}

pre, code {
    font-family: monospace;
    background-color: #f5f5f5;
    padding: 0.2em 0.4em;
}

pre {
    padding: 1em;
    overflow-x: auto;
    white-space: pre-wrap;
}

.essay-date {
    font-style: italic;
    color: #666;
    margin-bottom: 1em;
}
"""

# Sort orders
SORT_ORDER_ASC = "asc"
SORT_ORDER_DESC = "desc"
VALID_SORT_ORDERS = [SORT_ORDER_ASC, SORT_ORDER_DESC]

