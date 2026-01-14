"""
Parser for extracting and cleaning essay content from HTML.
"""

import re
import hashlib
from typing import List, Tuple, Optional
from urllib.parse import urljoin
from pathlib import Path
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image
import io

from .config import BASE_URL, IMAGES_CACHE_DIR


class ContentParser:
    """Extracts and cleans essay content from HTML."""
    
    def __init__(self, scraper=None):
        """
        Args:
            scraper: Scraper instance for downloading images (optional)
        """
        self.scraper = scraper
        self.downloaded_images = {}  # url -> local_path mapping
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def extract_title(self, soup: BeautifulSoup, fallback_title: str = "") -> str:
        """Extract the essay title from the page."""
        # Try various methods to find title
        
        # 1. Look for <title> tag
        title_tag = soup.find('title')
        if title_tag:
            title = self.clean_text(title_tag.get_text())
            if title and title.lower() not in ['', 'untitled', 'paul graham']:
                return title
        
        # 2. Look for first <h1> or large <font>
        for tag in soup.find_all(['h1', 'h2']):
            title = self.clean_text(tag.get_text())
            if title and len(title) > 3:
                return title
        
        # 3. Look for large bold text at the top
        for tag in soup.find_all(['b', 'strong'], limit=5):
            title = self.clean_text(tag.get_text())
            if title and len(title) > 5 and len(title) < 200:
                return title
        
        return fallback_title
    
    def download_image(self, img_url: str) -> Optional[Tuple[str, bytes]]:
        """
        Download an image and return (filename, image_data).
        Returns None if download fails or no scraper available.
        """
        if not self.scraper:
            return None
        
        # Skip spacer GIFs, tracking pixels, and navigation images
        skip_patterns = [
            'spacer.gif', 'pixel.gif', '1x1.', 'blank.gif',
            # PG's navigation bar images
            'trans_1x1.gif', 'essays-hierarchical.gif', 'rss-hierarchical.gif',
            # Small decorative images
            'dot.gif', 'bullet.gif', 'clear.gif'
        ]
        if any(pattern in img_url.lower() for pattern in skip_patterns):
            return None
        
        # Check cache
        if img_url in self.downloaded_images:
            cached_path = self.downloaded_images[img_url]
            if cached_path.exists():
                with open(cached_path, 'rb') as f:
                    return (cached_path.name, f.read())
        
        # Download image
        img_data = self.scraper.fetch_binary(img_url)
        if not img_data:
            return None
        
        # Validate it's actually an image and has reasonable size
        try:
            img = Image.open(io.BytesIO(img_data))
            width, height = img.size
            img.verify()
            
            # Skip very small images (likely decorative/navigation)
            if width < 50 or height < 50:
                return None
            # Skip images that look like navigation buttons (small width, tall height or vice versa)
            if (width < 150 and height < 30) or (height < 150 and width < 30):
                return None
        except Exception:
            return None
        
        # Generate filename from URL hash
        url_hash = hashlib.md5(img_url.encode()).hexdigest()
        
        # Determine extension from content type or URL
        extension = '.jpg'  # default
        if img_url.lower().endswith('.png'):
            extension = '.png'
        elif img_url.lower().endswith('.gif'):
            extension = '.gif'
        elif img_url.lower().endswith('.webp'):
            extension = '.webp'
        
        filename = f"{url_hash}{extension}"
        cache_path = IMAGES_CACHE_DIR / filename
        
        # Save to cache
        with open(cache_path, 'wb') as f:
            f.write(img_data)
        
        self.downloaded_images[img_url] = cache_path
        
        return (filename, img_data)
    
    def process_images(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, bytes]]:
        """
        Process all images in the content, download them, and update src attributes.
        Returns list of (filename, image_data) tuples.
        """
        images_data = []
        seen_filenames = set()  # Track to avoid duplicates
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                img.decompose()
                continue
            
            # Make absolute URL
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            # Download image
            result = self.download_image(src)
            if result:
                filename, img_data = result
                
                # Only add to images_data if not already seen
                if filename not in seen_filenames:
                    images_data.append((filename, img_data))
                    seen_filenames.add(filename)
                
                # Update src to reference embedded image (with correct path!)
                img['src'] = f"images/{filename}"
            else:
                # Remove image if download failed
                img.decompose()
        
        return images_data
    
    def convert_br_to_paragraphs(self, html_content: str) -> str:
        """
        Convert sequences of <br> tags to proper <p> tags.
        PG's essays often use <br><br> for paragraph breaks.
        """
        # Replace multiple br tags with paragraph markers
        html_content = re.sub(r'(<br\s*/?>[\s\n]*){2,}', '\n\n', html_content, flags=re.IGNORECASE)
        
        # Replace single br with newline
        html_content = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    def text_to_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs based on double newlines."""
        # Normalize whitespace
        text = re.sub(r'\r\n', '\n', text)
        # Split on double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)
        # Clean up each paragraph
        result = []
        for p in paragraphs:
            p = p.strip()
            # Normalize internal whitespace but keep single newlines
            p = re.sub(r'[ \t]+', ' ', p)
            if p and len(p) > 10:  # Skip very short paragraphs
                result.append(p)
        return result
    
    def remove_navigation(self, soup: BeautifulSoup) -> None:
        """Remove navigation elements from the soup."""
        # Navigation keywords to identify nav elements
        nav_keywords = ['home', 'essays', 'h&p', 'books', 'yc', 'arc', 'bel', 'lisp', 
                       'spam', 'responses', 'faqs', 'raqs', 'quotes', 'rss', 'bio', 
                       'twitter', 'mastodon', 'x.com']
        
        # Remove tables that look like navigation (contain mostly navigation links)
        for table in soup.find_all('table'):
            text = table.get_text(strip=True).lower()
            # If table text is short and contains multiple nav keywords, it's likely navigation
            if len(text) < 500:
                nav_count = sum(1 for kw in nav_keywords if kw in text)
                if nav_count >= 3:
                    table.decompose()
                    continue
            
            # Also check if table contains navigation-like link structure
            links = table.find_all('a')
            if len(links) >= 5:
                link_texts = [a.get_text(strip=True).lower() for a in links]
                nav_matches = sum(1 for lt in link_texts if lt in nav_keywords)
                if nav_matches >= 3:
                    table.decompose()
        
        # Remove images that look like navigation buttons
        for img in soup.find_all('img'):
            src = img.get('src', '').lower()
            alt = img.get('alt', '').lower()
            # Check if it's a navigation image
            if any(kw in src or kw in alt for kw in nav_keywords):
                img.decompose()
    
    def convert_plaintext_to_html(self, text: str) -> str:
        """Convert plain text (like ACL chapters) to HTML with proper paragraph structure."""
        lines = text.split('\n')
        html_parts = ['<div class="essay-content">']
        
        current_para = []
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Detect code blocks (lines starting with significant whitespace or special chars)
            if line.startswith('  ') and (';' in line or '(' in line or 'def' in line.lower()):
                if not in_code_block:
                    # Flush current paragraph
                    if current_para:
                        html_parts.append('<p>' + ' '.join(current_para) + '</p>')
                        current_para = []
                    html_parts.append('<pre><code>')
                    in_code_block = True
                html_parts.append(self.escape_html(line))
                html_parts.append('\n')
            else:
                if in_code_block:
                    html_parts.append('</code></pre>')
                    in_code_block = False
                
                if not stripped:
                    # Empty line - flush paragraph
                    if current_para:
                        html_parts.append('<p>' + ' '.join(current_para) + '</p>')
                        current_para = []
                else:
                    current_para.append(self.escape_html(stripped))
        
        # Flush remaining
        if in_code_block:
            html_parts.append('</code></pre>')
        if current_para:
            html_parts.append('<p>' + ' '.join(current_para) + '</p>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def extract_main_content(self, html: str, base_url: str, title: str = "") -> Tuple[str, List[Tuple[str, bytes]]]:
        """
        Extract the main essay content from HTML or plain text.
        
        Returns: (cleaned_html, list of (image_filename, image_data))
        Note: Returns just the content HTML, NOT wrapped in body/html tags.
        """
        # Check if this is plain text (not HTML)
        if not html.strip().startswith('<'):
            return self.convert_plaintext_to_html(html), []
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove navigation elements first
        self.remove_navigation(soup)
        
        # Find the main content area
        # PG's essays typically have content in <table> with specific structure
        
        content_candidates = []
        
        # Try to find tables that contain essay content
        for table in soup.find_all('table'):
            text = table.get_text(strip=True)
            if len(text) > 500:  # Substantial content
                content_candidates.append((len(text), table))
        
        # If no good tables, try body
        if not content_candidates:
            body = soup.find('body')
            if body:
                text = body.get_text(strip=True)
                content_candidates.append((len(text), body))
        
        # Sort by content length and take the largest
        if content_candidates:
            content_candidates.sort(reverse=True, key=lambda x: x[0])
            main_content = content_candidates[0][1]
        else:
            main_content = soup.find('body') or soup
        
        # Convert br tags to newlines in the HTML first
        content_html = str(main_content)
        content_html = self.convert_br_to_paragraphs(content_html)
        
        # Re-parse and extract text with proper paragraph preservation
        content_soup = BeautifulSoup(content_html, 'lxml')
        
        # Process images first (before we extract text)
        images_data = self.process_images(content_soup, base_url)
        
        # Remove "Related" links at the end of essays
        # These are typically <a> tags grouped together at the bottom
        # Find all anchor tags and remove those that look like standalone links
        for a_tag in content_soup.find_all('a'):
            link_text = a_tag.get_text(strip=True)
            parent = a_tag.parent
            
            # If the link is very short and appears to be standalone (not in a paragraph)
            # it's likely a "related" link
            if len(link_text) < 80:
                # Check if parent is a li, or if the link is mostly standalone
                if parent and parent.name in ['li', 'td', 'font']:
                    # Check if parent only contains this link (or links)
                    parent_text = parent.get_text(strip=True)
                    if parent_text == link_text or len(parent_text) < len(link_text) + 10:
                        a_tag.decompose()
                        continue
                
                # Also check if link is followed by whitespace/br only (standalone link)
                next_sib = a_tag.next_sibling
                prev_sib = a_tag.previous_sibling
                
                # If surrounded mostly by whitespace or other links, remove
                prev_is_link = isinstance(prev_sib, Tag) and prev_sib.name == 'a' if prev_sib else False
                next_is_link = isinstance(next_sib, Tag) and next_sib.name == 'a' if next_sib else False
                
                prev_is_ws = prev_sib is None or (isinstance(prev_sib, NavigableString) and not prev_sib.strip())
                next_is_ws = next_sib is None or (isinstance(next_sib, NavigableString) and not next_sib.strip())
                
                if (prev_is_link or prev_is_ws) and (next_is_link or next_is_ws):
                    # Likely part of a list of links
                    a_tag.decompose()
        
        # Create output container
        output_soup = BeautifulSoup('<div class="essay-content"></div>', 'lxml')
        container = output_soup.find('div')
        
        # Title to skip
        title_lower = title.lower().strip() if title else ""
        
        # Use get_text with separator to preserve structure
        # Replace font/b tags with markers to identify section headers
        for bold in content_soup.find_all(['b', 'strong']):
            text = bold.get_text(strip=True)
            if len(text) > 3 and len(text) < 100:
                # This might be a section header - add paragraph break before
                bold.insert_before('\n\n')
                bold.insert_after('\n\n')
        
        # Get text with newlines as separator
        raw_text = content_soup.get_text(separator='\n')
        
        # Split into paragraphs
        paragraphs = self.text_to_paragraphs(raw_text)
        
        # Navigation words to filter
        nav_words = ['want to start a startup? get funded by y combinator',
                     'home', 'essays', 'faq', 'raq', 'subscribe', 'twitter', 
                     'x.com', 'rss', 'mastodon', 'books', 'arc', 'bel', 'lisp']
        
        # YC ad phrases to skip
        yc_ad_phrases = [
            'get funded by', 'y combinator', 'want to start a startup',
            'get funded by y combinator'
        ]
        
        # Related links section markers
        related_markers = ['related:', 'related links:', 'see also:']
        
        # Date patterns to skip (we add date separately in build_chapter_html)
        date_patterns = [
            r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}(,\s*rev\.\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})?$',
            r'^\d{4}$',  # Just a year like "1993"
        ]
        
        in_related_section = False
        
        for para in paragraphs:
            para_lower = para.lower().strip()
            para_stripped = para.strip()
            
            # Check if we've hit the "Related:" section - skip everything after
            if any(marker in para_lower for marker in related_markers):
                in_related_section = True
                continue
            
            # Skip all content after "Related:" marker
            if in_related_section:
                continue
            
            # Skip title
            if para_lower == title_lower:
                continue
            
            # Skip navigation-like content
            if any(nav in para_lower for nav in nav_words) and len(para) < 100:
                continue
            
            # Skip YC ad content
            if any(phrase in para_lower for phrase in yc_ad_phrases) and len(para) < 50:
                continue
            
            # Skip standalone "." which is often leftover from links
            if para_stripped == '.' or para_stripped == ',':
                continue
            
            # Skip if it looks like a link title (short text that's a title of another essay)
            # These appear in "Related" sections even without the "Related:" header
            if len(para) < 60 and ':' in para and para.count(' ') < 8:
                # Check if it looks like "Author Re: Topic" or "Something Translation"
                if ' re: ' in para_lower or 'translation' in para_lower:
                    continue
            
            # Skip if it's just a date (we add date separately)
            is_date = False
            for pattern in date_patterns:
                if re.match(pattern, para_stripped, re.IGNORECASE):
                    is_date = True
                    break
            if is_date:
                continue
            
            # Create paragraph element
            p_tag = output_soup.new_tag('p')
            p_tag.string = para
            container.append(p_tag)
        
        # Post-process: Remove short, title-like paragraphs from the END
        # These are typically "Related:" links that appear without headers
        all_p_tags = container.find_all('p')
        
        # Work backwards from the end and remove short title-like paragraphs
        for p_tag in reversed(all_p_tags):
            text = p_tag.get_text(strip=True)
            
            # Stop if we hit a real paragraph (longer content ending with punctuation)
            if len(text) > 60 or (text.endswith('.') and len(text) > 30):
                break
            
            # Check if it looks like a link title (short, title-case, no sentence punctuation)
            words = text.split()
            if len(words) < 6 and len(text) < 50:
                # Skip legitimate section headers (usually in the middle, not at end)
                if all(w[0].isupper() or not w[0].isalpha() for w in words if len(w) > 1):
                    # Remove this link-like paragraph
                    p_tag.decompose()
                    continue
            
            # If it's very short and doesn't look like a sentence, remove
            if len(text) < 40 and not text.endswith('.'):
                p_tag.decompose()
                continue
            
            # Stop removing once we hit real content
            break
        
        # Return just the inner HTML of the container (no wrapper tags)
        return str(container), images_data
    
    def _copy_inner_content(self, source: Tag, dest: Tag, soup: BeautifulSoup):
        """Copy inner content from source to dest, preserving inline formatting."""
        for child in source.children:
            if isinstance(child, NavigableString):
                text = str(child)
                if text.strip():  # Only add non-empty text
                    dest.append(text)
            elif isinstance(child, Tag):
                if child.name in ['b', 'strong']:
                    new_tag = soup.new_tag('strong')
                    new_tag.string = child.get_text()
                    dest.append(new_tag)
                elif child.name in ['i', 'em']:
                    new_tag = soup.new_tag('em')
                    new_tag.string = child.get_text()
                    dest.append(new_tag)
                elif child.name == 'a':
                    new_tag = soup.new_tag('a')
                    if child.get('href'):
                        new_tag['href'] = child['href']
                    new_tag.string = child.get_text()
                    dest.append(new_tag)
                elif child.name == 'code':
                    new_tag = soup.new_tag('code')
                    new_tag.string = child.get_text()
                    dest.append(new_tag)
                elif child.name == 'img':
                    src = child.get('src', '')
                    if src:
                        new_tag = soup.new_tag('img', src=src)
                        if child.get('alt'):
                            new_tag['alt'] = child['alt']
                        dest.append(new_tag)
                elif child.name == 'br':
                    dest.append(soup.new_tag('br'))
                elif child.name in ['font', 'span']:
                    # Recursively process font/span content
                    self._copy_inner_content(child, dest, soup)
                else:
                    # For other tags, just get the text
                    text = child.get_text()
                    if text.strip():
                        dest.append(text)
    
    def build_chapter_html(self, title: str, content_html: str, date_str: Optional[str] = None) -> str:
        """
        Build complete chapter HTML with proper structure.
        Returns empty string if content is empty/invalid.
        """
        # Clean up the content - remove any wrapping body/html tags
        content_html = re.sub(r'</?html[^>]*>', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'</?body[^>]*>', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'</?head[^>]*>.*?</head>', '', content_html, flags=re.IGNORECASE | re.DOTALL)
        content_html = re.sub(r'</?table[^>]*>', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'</?tr[^>]*>', '', content_html, flags=re.IGNORECASE)
        content_html = re.sub(r'</?td[^>]*>', '', content_html, flags=re.IGNORECASE)
        
        # Check if content is empty after cleanup
        soup_check = BeautifulSoup(content_html, 'lxml')
        text_content = soup_check.get_text(strip=True)
        if not text_content or len(text_content) < 100:
            # Content is too short/empty, return empty to skip this chapter
            return ""
        
        # Re-parse content through BeautifulSoup to ensure valid XHTML
        content_soup = BeautifulSoup(content_html, 'lxml')
        # Get just the content, cleaned up
        clean_content = ''.join(str(tag) for tag in content_soup.body.children if tag.name)
        
        # Build proper XHTML structure (no XML declaration - ebooklib adds it)
        parts = [
            '<html xmlns="http://www.w3.org/1999/xhtml">',
            '<head>',
            '<title>' + self.escape_html(title) + '</title>',
            '<link rel="stylesheet" type="text/css" href="style.css"/>',
            '</head>',
            '<body>',
            '<h1>' + self.escape_html(title) + '</h1>',
        ]
        
        if date_str:
            parts.append(f'<p class="essay-date">{self.escape_html(str(date_str))}</p>')
        
        # Add content - ensure there's at least a paragraph
        if clean_content.strip():
            parts.append(clean_content)
        else:
            parts.append('<p>Content not available.</p>')
        
        parts.append('</body>')
        parts.append('</html>')
        
        return '\n'.join(parts)
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))
