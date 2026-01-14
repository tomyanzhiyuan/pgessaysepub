# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-14

### Added
- Initial release
- Scrape all essays from paulgraham.com/articles.html
- Generate Kobo-optimized EPUB files
- Custom cover image support (`--cover` option)
- Content caching for faster rebuilds
- Read/unread essay tracking via `state.json`
- CLI commands: `build`, `list`, `mark-read`, `mark-unread`, `reset`
- Date extraction from essay content
- Image embedding support
- Clean formatting optimized for e-ink displays

### Fixed
- Removed "Related:" link sections from essay endings
- Filtered out YC advertisement text
- Improved paragraph detection and whitespace handling
- Better date extraction from various formats

## [Unreleased]

### Planned
- Progress bar for long operations
- Configurable CSS themes
- Export reading progress to Kobo sync

