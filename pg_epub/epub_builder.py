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
    
    def create_book(self, custom_title: Optional[str] = None) -> epub.EpubBook:
        """Create and initialize a new EPUB book."""
        book = epub.EpubBook()
        
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
        
        # Create chapter
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"{chapter_id}.xhtml",
            lang=EPUB_LANGUAGE
        )
        
        chapter.content = content_html
        chapter.add_item(self.book.get_item_with_id('style'))
        
        # Add images
        for img_filename, img_data in images:
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
        sort_order: str = SORT_ORDER_DESC
    ) -> bool:
        """
        Build complete EPUB with unread and read sections.
        
        Args:
            unread_essays: List of essay dicts with keys: essay_state, content_html, images
            read_essays: List of essay dicts with keys: essay_state, content_html, images
            output_path: Path to write EPUB file
            sort_order: 'asc' or 'desc' for date sorting
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.create_book()
            
            # Sort essays
            unread_sorted = sorted(
                unread_essays,
                key=lambda x: (
                    0 if x['essay_state'].date else 1,
                    x['essay_state'].date or '',
                    x['essay_state'].title
                ),
                reverse=(sort_order == SORT_ORDER_DESC)
            )
            
            read_sorted = sorted(
                read_essays,
                key=lambda x: (
                    0 if x['essay_state'].date else 1,
                    x['essay_state'].date or '',
                    x['essay_state'].title
                ),
                reverse=(sort_order == SORT_ORDER_DESC)
            )
            
            # Build table of contents structure
            toc = []
            spine = ['nav']
            
            # Add unread section
            if unread_sorted:
                unread_chapters = []
                
                for essay_dict in unread_sorted:
                    essay = essay_dict['essay_state']
                    content_html = essay_dict['content_html']
                    images = essay_dict.get('images', [])
                    
                    # Build chapter title with [UNREAD] prefix
                    date_suffix = f" ({essay.raw_date_str or essay.date or 'Unknown date'})"
                    chapter_title = f"[UNREAD] {essay.title}{date_suffix}"
                    
                    # Create safe chapter ID
                    chapter_id = f"unread_{essay.essay_id.replace('.html', '').replace('/', '_')}"
                    
                    chapter = self.add_chapter(
                        chapter_id=chapter_id,
                        title=chapter_title,
                        content_html=content_html,
                        images=images
                    )
                    
                    unread_chapters.append(chapter)
                    spine.append(chapter)
                
                # Add unread section to TOC
                toc.append(
                    (epub.Section('Unread Essays'), unread_chapters)
                )
            
            # Add read section
            if read_sorted:
                read_chapters = []
                
                for essay_dict in read_sorted:
                    essay = essay_dict['essay_state']
                    content_html = essay_dict['content_html']
                    images = essay_dict.get('images', [])
                    
                    # Build chapter title with [READ] prefix
                    date_suffix = f" ({essay.raw_date_str or essay.date or 'Unknown date'})"
                    chapter_title = f"[READ] {essay.title}{date_suffix}"
                    
                    # Create safe chapter ID
                    chapter_id = f"read_{essay.essay_id.replace('.html', '').replace('/', '_')}"
                    
                    chapter = self.add_chapter(
                        chapter_id=chapter_id,
                        title=chapter_title,
                        content_html=content_html,
                        images=images
                    )
                    
                    read_chapters.append(chapter)
                    spine.append(chapter)
                
                # Add read section to TOC
                toc.append(
                    (epub.Section('Read Essays'), read_chapters)
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
            print(f"  - {len(unread_sorted)} unread essays")
            print(f"  - {len(read_sorted)} read essays")
            print(f"  - Total: {len(unread_sorted) + len(read_sorted)} essays")
            
            return True
            
        except Exception as e:
            print(f"Error building EPUB: {e}")
            import traceback
            traceback.print_exc()
            return False

