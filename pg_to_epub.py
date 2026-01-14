#!/usr/bin/env python3
"""
Paul Graham Essays to EPUB - CLI Entrypoint

Command-line tool for scraping Paul Graham's essays and building EPUB files.
"""

import sys
import argparse
from pathlib import Path
from typing import List

from pg_epub.config import SORT_ORDER_ASC, SORT_ORDER_DESC, VALID_SORT_ORDERS
from pg_epub.state import StateManager
from pg_epub.scraper import Scraper
from pg_epub.parser import ContentParser
from pg_epub.epub_builder import EpubBuilder
from pg_epub.cache import ContentCache


def cmd_build(args):
    """Build EPUB from all essays."""
    print("Paul Graham Essays to EPUB Builder")
    print("=" * 50)
    
    # Initialize components
    state = StateManager()
    scraper = Scraper()
    parser = ContentParser(scraper=scraper)
    builder = EpubBuilder()
    cache = ContentCache()
    
    # Check if using rebuild mode
    rebuild_mode = args.rebuild
    force_refresh = args.force_refresh
    
    # Handle force refresh - clear cache
    if force_refresh:
        print("\n[FORCE REFRESH] Clearing cache...")
        cleared = cache.clear_cache()
        print(f"Cleared {cleared} cached essays")
        rebuild_mode = False  # Force refresh means don't use rebuild mode
    
    if rebuild_mode:
        print("\n[REBUILD MODE] Using cached content")
        cache_stats = cache.get_cache_stats()
        print(f"Cache: {cache_stats['cached_essays']} essays ({cache_stats['total_size_mb']} MB)")
        
        # Check if we have state
        if not state.essays:
            print("Error: No state found. Run without --rebuild first to fetch essays.")
            return 1
        
        essays_list = [
            {
                'id': e.essay_id,
                'title': e.title,
                'url': e.url,
                'date': e.date,
                'raw_date_str': e.raw_date_str
            }
            for e in state.get_all_essays()
        ]
    else:
        # Step 1: Fetch essay list
        print("\n[1/4] Fetching essay list from paulgraham.com...")
        essays_list = scraper.fetch_essay_list()
        
        if not essays_list:
            print("Error: Could not fetch essay list")
            return 1
        
        print(f"Found {len(essays_list)} essays")
        
        # Step 2: Update state with new essays
        print("\n[2/4] Updating essay metadata...")
        for essay_data in essays_list:
            state.update_essay(
                essay_id=essay_data['id'],
                title=essay_data['title'],
                url=essay_data['url'],
                date=essay_data['date'],
                raw_date_str=essay_data['raw_date_str']
            )
        
        state.save()
        print(f"State updated with {len(state.essays)} essays")
    
    # Step 3: Fetch/Load content for all essays
    step_num = "[3/4]" if not rebuild_mode else "[1/2]"
    if rebuild_mode:
        print(f"\n{step_num} Loading essay content from cache...")
    else:
        print(f"\n{step_num} Fetching and parsing essay content...")
        print("This may take a few minutes...")
    
    unread_essays = []
    read_essays = []
    
    total = len(essays_list)
    fetched_count = 0
    cached_count = 0
    
    for idx, essay_data in enumerate(essays_list, 1):
        essay_id = essay_data['id']
        essay_state = state.get_essay(essay_id)
        
        if not essay_state:
            continue
        
        print(f"  [{idx}/{total}] {essay_state.title[:60]}...", end='', flush=True)
        
        # Try to load from cache first if in rebuild mode
        content_html = None
        images = []
        
        if rebuild_mode:
            cached_data = cache.load_essay_content(essay_id)
            if cached_data:
                content_html, images = cached_data
                cached_count += 1
                print(f" [CACHED, {len(images)} images]")
            else:
                print(" [NOT CACHED - SKIPPING]")
                continue
        else:
            # Try cache first even in normal mode
            cached_data = cache.load_essay_content(essay_id)
            if cached_data:
                content_html, images = cached_data
                cached_count += 1
                print(f" [CACHED, {len(images)} images]")
            else:
                # Fetch content
                html, extracted_date, extracted_raw_date = scraper.fetch_essay_content(essay_state.url)
                
                if not html:
                    print(" [FAILED]")
                    continue
                
                # Update date from essay content (always prefer this over index page date)
                if extracted_date:
                    essay_state.date = extracted_date
                    essay_state.raw_date_str = extracted_raw_date
                
                # Parse content
                content_html, images = parser.extract_main_content(
                    html=html,
                    base_url=essay_state.url,
                    title=essay_state.title
                )
                
                # Cache the parsed content
                cache.save_essay_content(essay_id, content_html, images)
                fetched_count += 1
                print(f" [OK, {len(images)} images]")
        
        # Build complete chapter HTML
        chapter_html = parser.build_chapter_html(
            title=essay_state.title,
            content_html=content_html,
            date_str=essay_state.raw_date_str or essay_state.date
        )
        
        # Skip essays with empty/invalid content
        if not chapter_html:
            print(f" [SKIPPED - empty content]")
            continue
        
        essay_dict = {
            'essay_state': essay_state,
            'content_html': chapter_html,
            'images': images
        }
        
        if essay_state.read:
            read_essays.append(essay_dict)
        else:
            unread_essays.append(essay_dict)
    
    # Save updated state
    state.save()
    
    # Print stats
    if not rebuild_mode and (fetched_count > 0 or cached_count > 0):
        print(f"\nContent summary: {fetched_count} fetched, {cached_count} from cache")
    
    # Step 4: Build EPUB
    step_num = "[4/4]" if not rebuild_mode else "[2/2]"
    print(f"\n{step_num} Building EPUB...")
    print(f"  - Unread essays: {len(unread_essays)}")
    print(f"  - Read essays: {len(read_essays)}")
    print(f"  - Sort order: {args.order}")
    
    output_path = Path(args.output)
    cover_path = Path(args.cover) if args.cover else None
    
    success = builder.build_epub(
        unread_essays=unread_essays,
        read_essays=read_essays,
        output_path=output_path,
        sort_order=args.order,
        cover_image_path=cover_path
    )
    
    if success:
        print(f"\n{'=' * 50}")
        print(f"Success! Your EPUB is ready:")
        print(f"  {output_path.absolute()}")
        print(f"\nYou can now copy this file to your Kobo via USB.")
        return 0
    else:
        print("\nError: Failed to build EPUB")
        return 1


def cmd_list(args):
    """List all essays with read/unread status."""
    state = StateManager()
    
    if not state.essays:
        print("No essays found. Run 'build' first to fetch essay list.")
        return 1
    
    essays = state.get_all_essays()
    
    if args.unread_only:
        essays = [e for e in essays if not e.read]
    elif args.read_only:
        essays = [e for e in essays if e.read]
    
    # Sort by date
    essays_sorted = sorted(
        essays,
        key=lambda e: (0 if e.date else 1, e.date or '', e.title),
        reverse=True
    )
    
    print(f"Paul Graham Essays ({len(essays_sorted)} total)")
    print("=" * 80)
    
    for essay in essays_sorted:
        status = "[READ]  " if essay.read else "[UNREAD]"
        date_str = essay.raw_date_str or essay.date or "Unknown date"
        print(f"{status} {essay.title[:50]:50} | {date_str:15} | {essay.essay_id}")
    
    print(f"\nTotal: {len(essays_sorted)} essays")
    unread_count = len([e for e in essays if not e.read])
    read_count = len([e for e in essays if e.read])
    print(f"  Unread: {unread_count}")
    print(f"  Read: {read_count}")
    
    return 0


def cmd_mark_read(args):
    """Mark essays as read."""
    state = StateManager()
    
    essay_ids = []
    
    # Collect essay IDs from --id flag
    if args.id:
        essay_ids.extend(args.id)
    
    # Collect essay IDs from --title flag (search by title)
    if args.title:
        for title_query in args.title:
            found = state.find_essays_by_title(title_query)
            if found:
                essay_ids.extend(found)
                print(f"Found {len(found)} essays matching '{title_query}'")
            else:
                print(f"Warning: No essays found matching '{title_query}'")
    
    if not essay_ids:
        print("Error: No essays specified. Use --id or --title")
        return 1
    
    # Remove duplicates
    essay_ids = list(set(essay_ids))
    
    # Mark as read
    count = state.mark_read(essay_ids)
    state.save()
    
    print(f"\nMarked {count} essay(es) as read:")
    for essay_id in essay_ids:
        essay = state.get_essay(essay_id)
        if essay:
            print(f"  ✓ {essay.title}")
    
    return 0


def cmd_mark_unread(args):
    """Mark essays as unread."""
    state = StateManager()
    
    essay_ids = []
    
    # Collect essay IDs from --id flag
    if args.id:
        essay_ids.extend(args.id)
    
    # Collect essay IDs from --title flag (search by title)
    if args.title:
        for title_query in args.title:
            found = state.find_essays_by_title(title_query)
            if found:
                essay_ids.extend(found)
                print(f"Found {len(found)} essays matching '{title_query}'")
            else:
                print(f"Warning: No essays found matching '{title_query}'")
    
    if not essay_ids:
        print("Error: No essays specified. Use --id or --title")
        return 1
    
    # Remove duplicates
    essay_ids = list(set(essay_ids))
    
    # Mark as unread
    count = state.mark_unread(essay_ids)
    state.save()
    
    print(f"\nMarked {count} essay(es) as unread:")
    for essay_id in essay_ids:
        essay = state.get_essay(essay_id)
        if essay:
            print(f"  ✓ {essay.title}")
    
    return 0


def cmd_reset(args):
    """Reset all state."""
    state = StateManager()
    
    if not args.confirm:
        print("This will clear all read/unread state and cached data.")
        response = input("Are you sure? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return 0
    
    state.reset()
    print("State has been reset.")
    return 0


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Scrape Paul Graham's essays and build a Kobo-friendly EPUB",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build EPUB from all essays')
    build_parser.add_argument(
        '--output', '-o',
        default='pg_essays.epub',
        help='Output EPUB file path (default: pg_essays.epub)'
    )
    build_parser.add_argument(
        '--order',
        choices=VALID_SORT_ORDERS,
        default=SORT_ORDER_DESC,
        help=f"Sort order: '{SORT_ORDER_ASC}' (oldest first) or '{SORT_ORDER_DESC}' (newest first, default)"
    )
    build_parser.add_argument(
        '--cover', '-c',
        help='Path to cover image file (JPG, PNG, GIF, or WEBP)'
    )
    build_parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild EPUB from cached content (fast, no fetching)'
    )
    build_parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Force re-download of all essays (ignore cache)'
    )
    build_parser.set_defaults(func=cmd_build)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all essays with read/unread status')
    list_parser.add_argument(
        '--unread-only',
        action='store_true',
        help='Show only unread essays'
    )
    list_parser.add_argument(
        '--read-only',
        action='store_true',
        help='Show only read essays'
    )
    list_parser.set_defaults(func=cmd_list)
    
    # Mark-read command
    mark_read_parser = subparsers.add_parser('mark-read', help='Mark essays as read')
    mark_read_parser.add_argument(
        '--id',
        nargs='+',
        help='Essay IDs (filenames like avg.html)'
    )
    mark_read_parser.add_argument(
        '--title',
        nargs='+',
        help='Essay titles (partial match, case-insensitive)'
    )
    mark_read_parser.set_defaults(func=cmd_mark_read)
    
    # Mark-unread command
    mark_unread_parser = subparsers.add_parser('mark-unread', help='Mark essays as unread')
    mark_unread_parser.add_argument(
        '--id',
        nargs='+',
        help='Essay IDs (filenames like avg.html)'
    )
    mark_unread_parser.add_argument(
        '--title',
        nargs='+',
        help='Essay titles (partial match, case-insensitive)'
    )
    mark_unread_parser.set_defaults(func=cmd_mark_unread)
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset all state')
    reset_parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    reset_parser.set_defaults(func=cmd_reset)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Run command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

