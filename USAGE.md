# Quick Start Guide

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /Users/tomyanzhiyuan/GitHub/pgessaysepub
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

### Generate Your First EPUB

```bash
python pg_to_epub.py build --output my_pg_essays.epub
```

This will:
- Scrape all ~229 essays from paulgraham.com
- Extract clean content with embedded images
- Generate an EPUB file with all essays marked as [UNREAD]
- Save to `my_pg_essays.epub` in the current directory

**Note**: The first run will take 5-15 minutes as it downloads all essays. Be patient!

### List All Essays

```bash
python pg_to_epub.py list
```

View all essays with their read/unread status, dates, and IDs.

### Mark Essays as Read

After reading an essay on your Kobo, mark it as read:

**By essay ID (filename):**
```bash
python pg_to_epub.py mark-read --id greatwork.html kids.html
```

**By title (partial match, case-insensitive):**
```bash
python pg_to_epub.py mark-read --title "Great Work" "Having Kids"
```

### Regenerate EPUB with Updated Status

After marking essays as read, regenerate the EPUB:

```bash
python pg_to_epub.py build --output my_pg_essays.epub
```

Now the EPUB will have:
- **Unread Essays** section (essays you haven't read yet)
- **Read Essays** section (essays you've marked as read)

### Mark Essays as Unread

Want to re-read an essay? Mark it as unread:

```bash
python pg_to_epub.py mark-unread --id greatwork.html
```

## Advanced Options

### Sort Order

**Newest first (default):**
```bash
python pg_to_epub.py build --order desc
```

**Oldest first:**
```bash
python pg_to_epub.py build --order asc
```

### List Only Unread Essays

```bash
python pg_to_epub.py list --unread-only
```

### Reset Everything

To start fresh (clears all read/unread state):

```bash
python pg_to_epub.py reset
```

## Typical Workflow

### First Time Setup
1. Install dependencies (one time)
2. Run `python pg_to_epub.py build`
3. Copy the EPUB to your Kobo via USB
4. Start reading!

### Regular Updates (Every Few Months)
1. Read essays on your Kobo
2. When you want to update:
   ```bash
   # Mark what you've read
   python pg_to_epub.py mark-read --title "Essay Title 1" "Essay Title 2"
   
   # Regenerate EPUB
   python pg_to_epub.py build
   
   # Copy updated EPUB to Kobo
   ```

3. The new EPUB will have your read essays in the "Read Essays" section

## Tips

- **Finding Essay IDs**: Run `python pg_to_epub.py list` to see all essay IDs (the filenames like `greatwork.html`)
- **Partial Title Matching**: You don't need to type the full title when using `--title`, just enough to uniquely identify it
- **Multiple Essays**: You can mark multiple essays at once by listing multiple IDs or titles
- **State File**: Your read/unread state is stored in `state.json` - keep this file to preserve your reading progress

## File Locations

- **EPUB output**: Specified by `--output` flag (default: `pg_essays.epub` in current directory)
- **State file**: `state.json` in the project root
- **Cache**: `.cache/` directory (images and temporary files)

## Troubleshooting

**Issue**: Command not found
- **Solution**: Make sure your virtual environment is activated: `source venv/bin/activate`

**Issue**: "No module named 'requests'"
- **Solution**: Install dependencies: `pip install -r requirements.txt`

**Issue**: EPUB generation is slow
- **Solution**: This is normal for the first run. Subsequent runs will be faster as dates and metadata are cached.

**Issue**: Some essay dates show "Unknown date"
- **Solution**: Some older essays don't have clear publication dates. They'll be grouped at the end within their section.

## Next Steps

- Check out the full [README.md](README.md) for more details
- All essay content is © Paul Graham
- This tool is for personal educational use
