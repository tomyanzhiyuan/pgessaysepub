"""
EPUB builder for compiling essays into a Kobo-friendly ebook.
"""

from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from ebooklib import epub

from .config import (
    EPUB_TITLE,
    EPUB_AUTHOR,
    EPUB_LANGUAGE,
    EPUB_PUBLISHER,
    EPUB_CSS,
    SORT_ORDER_ASC,
    SORT_ORDER_DESC
)
from .state import EssayState


class EpubBuilder:
    """Builds EPUB files from essay content."""
    
    def __init__(self):
        self.book = None
        self.added_images = set()  # Track added image filenames to avoid duplicates
    
    def create_book(self, custom_title: Optional[str] = None) -> epub.EpubBook:
        """Create and initialize a new EPUB book."""
        book = epub.EpubBook()
        self.added_images = set()  # Reset for new book
        
        # Set metadata
        title = custom_title or f"{EPUB_TITLE} - {datetime.now().strftime('%Y-%m-%d')}"
        book.set_identifier(f"pg-essays-{datetime.now().strftime('%Y%m%d')}")
        book.set_title(title)
        book.set_language(EPUB_LANGUAGE)
        book.add_author(EPUB_AUTHOR)
        book.add_metadata('DC', 'publisher', EPUB_PUBLISHER)
        
        # Add CSS
        css = epub.EpubItem(
            uid="style",
            file_name="style.css",
            media_type="text/css",
            content=EPUB_CSS
        )
        book.add_item(css)
        
        self.book = book
        return book
    
    def set_cover(self, cover_image_path: Path) -> Optional[epub.EpubHtml]:
        """
        Set the cover image for the EPUB and return cover page for spine.
        
        Args:
            cover_image_path: Path to the cover image file
        
        Returns:
            Cover HTML page if successful, None otherwise
        """
        if not cover_image_path.exists():
            print(f"Warning: Cover image not found: {cover_image_path}")
            return None
        
        try:
            # Read cover image
            with open(cover_image_path, 'rb') as f:
                cover_data = f.read()
            
            # Determine media type and filename
            suffix = cover_image_path.suffix.lower()
            media_type = "image/jpeg"
            if suffix in ['.jpg', '.jpeg']:
                media_type = "image/jpeg"
            elif suffix == '.png':
                media_type = "image/png"
            elif suffix == '.gif':
                media_type = "image/gif"
            elif suffix == '.webp':
                media_type = "image/webp"
            
            # Set cover - this creates cover-img and cover.xhtml
            self.book.set_cover("cover" + suffix, cover_data)
            
            # Get the cover page that was created
            cover_page = self.book.get_item_with_id('cover')
            
            print(f"✓ Cover image added: {cover_image_path.name}")
            return cover_page
            
        except Exception as e:
            print(f"Warning: Could not set cover image: {e}")
            return None
    
    def add_chapter(
        self,
        chapter_id: str,
        title: str,
        content_html: str,
        images: List[Tuple[str, bytes]] = None
    ) -> epub.EpubHtml:
        """
        Add a chapter to the book.
        
        Args:
            chapter_id: Unique identifier for the chapter
            title: Chapter title
            content_html: HTML content
            images: List of (filename, image_data) tuples
        
        Returns:
            The created EpubHtml chapter
        """
        if images is None:
            images = []
        
        # Validate content is not empty/invalid
        from lxml import html as lxml_html
        try:
            # Test if content can be parsed - must have body content
            test_doc = lxml_html.document_fromstring(content_html)
            body = test_doc.find('.//body')
            if body is None or not body.text_content().strip():
                print(f"  [SKIPPING {chapter_id} - empty body]")
                return None
        except Exception as e:
            print(f"  [SKIPPING {chapter_id} - invalid HTML: {e}]")
            return None
        
        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"{chapter_id}.xhtml",
            lang=EPUB_LANGUAGE
        )
        
        chapter.content = content_html
        chapter.add_item(self.book.get_item_with_id('style'))
        
        # Add images (skip duplicates)
        for img_filename, img_data in images:
            # Skip if already added
            if img_filename in self.added_images:
                continue
            
            # Determine media type
            media_type = "image/jpeg"
            if img_filename.lower().endswith('.png'):
                media_type = "image/png"
            elif img_filename.lower().endswith('.gif'):
                media_type = "image/gif"
            elif img_filename.lower().endswith('.webp'):
                media_type = "image/webp"
            
            # Create image item
            img_item = epub.EpubItem(
                uid=f"img_{img_filename}",
                file_name=f"images/{img_filename}",
                media_type=media_type,
                content=img_data
            )
            
            self.book.add_item(img_item)
            self.added_images.add(img_filename)
        
        self.book.add_item(chapter)
        return chapter
    
    def sort_essays(
        self,
        essays: List[EssayState],
        order: str = SORT_ORDER_DESC
    ) -> List[EssayState]:
        """
        Sort essays by publication date.
        
        Args:
            essays: List of essay states
            order: 'asc' for oldest first, 'desc' for newest first
        
        Returns:
            Sorted list of essays
        """
        # Sort by date, with None dates at the end
        def sort_key(essay: EssayState) -> Tuple:
            if essay.date:
                return (0, essay.date)
            else:
                # No date - sort to end, then by title
                return (1, essay.title)
        
        reverse = (order == SORT_ORDER_DESC)
        return sorted(essays, key=sort_key, reverse=reverse)
    
    def build_epub(
        self,
        unread_essays: List[Dict],
        read_essays: List[Dict],
        output_path: Path,
        sort_order: str = SORT_ORDER_DESC,
        cover_image_path: Optional[Path] = None
    ) -> bool:
        """
        Build complete EPUB with unread and read sections.
        
        Args:
            unread_essays: List of essay dicts with keys: essay_state, content_html, images
            read_essays: List of essay dicts with keys: essay_state, content_html, images
            output_path: Path to write EPUB file
            sort_order: 'asc' or 'desc' for date sorting
            cover_image_path: Optional path to cover image file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.create_book()
            
            # Set cover if provided and get cover page for spine
            cover_page = None
            if cover_image_path:
                cover_page = self.set_cover(cover_image_path)
            
            # Combine all essays (no separate unread/read sections since Kobo can't sync status)
            all_essays = unread_essays + read_essays
            
            # Sort essays: with dates first (by date), then without dates at end (by title)
            essays_with_dates = [e for e in all_essays if e['essay_state'].date]
            essays_without_dates = [e for e in all_essays if not e['essay_state'].date]
            
            # Sort essays with dates by date
            essays_with_dates.sort(
                key=lambda x: (x['essay_state'].date, x['essay_state'].title),
                reverse=(sort_order == SORT_ORDER_DESC)
            )
            
            # Sort essays without dates by title
            essays_without_dates.sort(key=lambda x: x['essay_state'].title)
            
            # Combine: dated essays first, then no-date essays at end
            all_sorted = essays_with_dates + essays_without_dates
            
            # Build table of contents structure
            toc = []
            spine = []
            
            # Add cover first in spine if we have one
            if cover_page:
                spine.append(cover_page)
            
            spine.append('nav')
            
            # Add all essays (no [UNREAD]/[READ] tags since Kobo can't update status)
            all_chapters = []
            
            for essay_dict in all_sorted:
                essay = essay_dict['essay_state']
                content_html = essay_dict['content_html']
                images = essay_dict.get('images', [])
                
                # Build chapter title - only add date if we have one
                if essay.raw_date_str:
                    chapter_title = f"{essay.title} ({essay.raw_date_str})"
                elif essay.date:
                    chapter_title = f"{essay.title} ({essay.date})"
                else:
                    chapter_title = essay.title
                
                # Create safe chapter ID
                chapter_id = f"essay_{essay.essay_id.replace('.html', '').replace('/', '_')}"
                
                chapter = self.add_chapter(
                    chapter_id=chapter_id,
                    title=chapter_title,
                    content_html=content_html,
                    images=images
                )
                
                if chapter:  # Skip if add_chapter returned None
                    all_chapters.append(chapter)
                    spine.append(chapter)
            
            # Add all essays to TOC (single section)
            if all_chapters:
                toc.append(
                    (epub.Section('Essays'), all_chapters)
                )
            
            # Set TOC and spine
            self.book.toc = toc
            self.book.spine = spine
            
            # Add required navigation files
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())
            
            # Write EPUB file
            epub.write_epub(str(output_path), self.book)
            
            print(f"\n✓ EPUB created successfully: {output_path}")
            print(f"  - {len(all_chapters)} essays")
            
            return True
            
        except Exception as e:
            print(f"Error building EPUB: {e}")
            import traceback
            traceback.print_exc()
            return False

