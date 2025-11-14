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
        
        # Validate it's actually an image
        try:
            img = Image.open(io.BytesIO(img_data))
            img.verify()
        except Exception:
            print(f"Invalid image data from {img_url}")
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
        
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # Make absolute URL
            if not src.startswith('http'):
                src = urljoin(base_url, src)
            
            # Download image
            result = self.download_image(src)
            if result:
                filename, img_data = result
                images_data.append((filename, img_data))
                
                # Update src to reference embedded image
                img['src'] = filename
            else:
                # Remove image if download failed
                img.decompose()
        
        return images_data
    
    def extract_main_content(self, html: str, base_url: str, title: str = "") -> Tuple[str, List[Tuple[str, bytes]]]:
        """
        Extract the main essay content from HTML.
        
        Returns: (cleaned_html, list of (image_filename, image_data))
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract title if not provided
        if not title:
            title = self.extract_title(soup, "Untitled Essay")
        
        # Find the main content area
        # PG's essays typically have content in <table> with specific structure
        # or sometimes just in the <body>
        
        # Strategy: Find the largest block of paragraph text
        # Look for container with most <p> or <font> tags containing substantial text
        
        content_candidates = []
        
        # Try to find tables that contain essay content
        for table in soup.find_all('table'):
            # Count text content
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
            # Fallback to body
            main_content = soup.find('body') or soup
        
        # Create a new soup with cleaned content
        cleaned_soup = BeautifulSoup('<html><body></body></html>', 'lxml')
        body = cleaned_soup.find('body')
        
        # Add title
        title_tag = cleaned_soup.new_tag('h1')
        title_tag.string = title
        body.append(title_tag)
        
        # Extract paragraphs, lists, and other content elements
        for element in main_content.find_all(['p', 'font', 'br', 'blockquote', 'ul', 'ol', 'pre', 'img', 'h1', 'h2', 'h3']):
            # Skip navigation, headers, footers
            text = element.get_text(strip=True)
            
            # Skip elements with very little content (likely navigation)
            if element.name in ['p', 'font'] and len(text) < 10:
                # Check if it's just a date or navigation
                if any(nav_word in text.lower() for nav_word in ['home', 'essays', 'faq', 'raq', 'subscribe', 'twitter']):
                    continue
            
            # Skip if it's just the title repeated
            if element.name in ['h1', 'h2'] and text == title:
                continue
            
            # Convert font tags to p tags if they have content
            if element.name == 'font' and len(text) > 20:
                p_tag = cleaned_soup.new_tag('p')
                p_tag.string = text
                body.append(p_tag)
            elif element.name == 'br':
                # Skip standalone br tags
                continue
            elif element.name == 'img':
                # Keep images
                img_tag = cleaned_soup.new_tag('img', src=element.get('src', ''))
                if element.get('alt'):
                    img_tag['alt'] = element['alt']
                body.append(img_tag)
            elif element.name in ['p', 'blockquote', 'ul', 'ol', 'pre', 'h2', 'h3']:
                # Clone the element
                new_elem = cleaned_soup.new_tag(element.name)
                
                # Copy text and nested tags
                for child in element.descendants:
                    if isinstance(child, NavigableString):
                        new_elem.append(child.string if hasattr(child, 'string') else str(child))
                    elif isinstance(child, Tag) and child.name in ['b', 'i', 'strong', 'em', 'code', 'a', 'li', 'img']:
                        # Clone simple inline tags
                        child_clone = cleaned_soup.new_tag(child.name)
                        if child.name == 'a' and child.get('href'):
                            child_clone['href'] = child['href']
                        elif child.name == 'img' and child.get('src'):
                            child_clone['src'] = child['src']
                        child_clone.string = child.get_text()
                        new_elem.append(child_clone)
                
                if new_elem.get_text(strip=True):  # Only add if has content
                    body.append(new_elem)
        
        # Process images (download and embed)
        images_data = self.process_images(cleaned_soup, base_url)
        
        # Return cleaned HTML
        html_output = str(cleaned_soup.find('body'))
        
        return html_output, images_data
    
    def build_chapter_html(self, title: str, content_html: str, date_str: Optional[str] = None) -> str:
        """
        Build complete chapter HTML with title and content.
        """
        html_parts = ['<html><head><meta charset="UTF-8"/></head><body>']
        
        html_parts.append(f'<h1>{self.escape_html(title)}</h1>')
        
        if date_str:
            html_parts.append(f'<p class="essay-date">{self.escape_html(date_str)}</p>')
        
        html_parts.append(content_html)
        
        html_parts.append('</body></html>')
        
        return '\n'.join(html_parts)
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

