"""
Scraper for fetching essay list and content from paulgraham.com.
"""

import re
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from .config import (
    ARTICLES_INDEX_URL,
    BASE_URL,
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY
)


class Scraper:
    """Scrapes Paul Graham's website for essays."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL."""
        try:
            time.sleep(REQUEST_DELAY)  # Be polite
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def fetch_binary(self, url: str, silent: bool = False) -> Optional[bytes]:
        """Fetch binary content (e.g., images) from a URL."""
        try:
            time.sleep(REQUEST_DELAY)
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except Exception as e:
            # Only print errors for non-known-missing images
            if not silent:
                # Known missing images - silently skip
                known_missing = ['spacer.gif', 'y18.gif', 'pixel.gif', '1x1.']
                if not any(known in url.lower() for known in known_missing):
                    print(f"Error fetching binary {url}: {e}")
            return None
    
    def parse_date_string(self, date_str: str) -> Tuple[Optional[str], str]:
        """
        Parse a date string into ISO format (YYYY-MM-DD) and keep original.
        
        Returns: (iso_date, raw_date_str)
        """
        if not date_str:
            return None, ""
        
        date_str = date_str.strip()
        
        # Common patterns on PG's site:
        # "January 2003"
        # "April 2001"
        # "2003"
        
        # Try full month + year
        match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            month_name = match.group(1)
            year = match.group(2)
            month_map = {
                'january': '01', 'february': '02', 'march': '03',
                'april': '04', 'may': '05', 'june': '06',
                'july': '07', 'august': '08', 'september': '09',
                'october': '10', 'november': '11', 'december': '12'
            }
            month = month_map.get(month_name.lower(), '01')
            return f"{year}-{month}-01", date_str
        
        # Try just year
        match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
        if match:
            year = match.group(1)
            return f"{year}-01-01", date_str
        
        return None, date_str
    
    def fetch_essay_list(self) -> List[Dict[str, str]]:
        """
        Fetch the list of essays from the articles index page.
        
        Returns: List of dicts with keys: id, title, url, date, raw_date_str
        """
        html = self.fetch_url(ARTICLES_INDEX_URL)
        if not html:
            print("Failed to fetch articles index page")
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        essays = []
        
        # The articles page has a specific structure
        # Look for links in the font tags within table cells
        # The structure is typically: <a href="essay.html">Title</a>
        
        # Find all links in the main content
        # PG's articles page has links in a table structure
        links = soup.find_all('a', href=True)
        
        seen_urls = set()
        
        for link in links:
            href = link.get('href', '')
            
            # Skip non-essay links (index, rss, etc.)
            skip_pages = ['index.html', 'rss.html', 'faq.html', 'raq.html', 'bio.html', 'quo.html']
            if not href:
                continue
            if href in skip_pages or href.startswith('#'):
                continue
            # Allow external URLs only for ACL chapters (on CDN)
            if href.startswith('http') and 'paulgraham/acl' not in href:
                continue
            
            # Skip if already seen
            if href in seen_urls:
                continue
            
            # Must be an HTML or TXT file (check without query params)
            href_base = href.split('?')[0]
            if not href_base.endswith('.html') and not href_base.endswith('.txt'):
                continue
            
            # Get title from link text
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            # Build full URL
            full_url = urljoin(BASE_URL, href)
            
            # Try to find date near the link
            # On PG's site, dates are often in the same table cell or nearby
            date_str = None
            parent = link.parent
            if parent:
                # Look for date patterns in the parent element's text
                parent_text = parent.get_text()
                # Try to extract date from parent text
                date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', parent_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(0)
                else:
                    # Try just year
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', parent_text)
                    if year_match:
                        date_str = year_match.group(0)
            
            iso_date, raw_date = self.parse_date_string(date_str) if date_str else (None, "")
            
            # Handle external URLs (like ACL chapters on CDN)
            if href.startswith('http'):
                full_url = href
                # Extract ID from URL (e.g., acl1.txt from the CDN URL)
                import os
                essay_id = os.path.basename(href.split('?')[0])  # Remove query params
            else:
                essay_id = href  # Use filename as ID
            
            essays.append({
                'id': essay_id,
                'title': title,
                'url': full_url,
                'date': iso_date,
                'raw_date_str': raw_date
            })
            
            seen_urls.add(essay_id)  # Use essay_id for dedup
        
        print(f"Found {len(essays)} essays on index page")
        return essays
    
    def extract_date_from_essay(self, soup: BeautifulSoup) -> Tuple[Optional[str], str]:
        """
        Try to extract publication date from an essay page.
        PG puts dates at the very start of the content, typically like:
        <font size="2" face="verdana">July 2023<br /><br />...
        or:
        <font size="2" face="verdana">March 2008, rev. June 2008<br /><br />...
        or just a year:
        <font size="2" face="verdana">1993...
        """
        # Find the main content font tag (size=2, face=verdana)
        content_font = soup.find('font', {'size': '2', 'face': 'verdana'})
        if content_font:
            # Get the raw HTML and look for date at the very start
            content_html = str(content_font)
            
            # Pattern 1: Month Year (with optional revision)
            date_pattern = r'>([A-Z][a-z]+ \d{4}(?:, rev\. [A-Z][a-z]+ \d{4})?)\s*<br'
            match = re.search(date_pattern, content_html)
            if match:
                return self.parse_date_string(match.group(1))
            
            # Pattern 2: Just a year at the start (like "1993" or "2001")
            year_pattern = r'>\s*(\d{4})\s*(?:<|[\n\r])'
            match = re.search(year_pattern, content_html[:200])
            if match:
                return self.parse_date_string(match.group(1))
        
        # Fallback: search for date pattern in first 500 chars of any font tag
        for tag in soup.find_all('font', limit=5):
            html_str = str(tag)[:500]
            
            # Month Year pattern
            match = re.search(r'>([A-Z][a-z]+ \d{4}(?:, rev\. [A-Z][a-z]+ \d{4})?)\s*<br', html_str)
            if match:
                return self.parse_date_string(match.group(1))
            
            # Just year pattern
            match = re.search(r'>\s*(\d{4})\s*(?:<|[\n\r])', html_str[:200])
            if match:
                return self.parse_date_string(match.group(1))
        
        # Final fallback: search in text content
        for tag in soup.find_all(['font', 'p', 'div'], limit=10):
            text = tag.get_text(strip=True)[:200]
            # Month Year
            date_match = re.search(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', text, re.IGNORECASE)
            if date_match:
                return self.parse_date_string(date_match.group(0))
            # Just year at the start
            year_match = re.match(r'^(\d{4})\s', text)
            if year_match:
                return self.parse_date_string(year_match.group(1))
        
        return None, ""
    
    def fetch_essay_content(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Fetch an essay's full content.
        
        Returns: (html_content, date, raw_date_str)
        """
        html = self.fetch_url(url)
        if not html:
            return None, None, None
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Try to extract date if not already known
        iso_date, raw_date = self.extract_date_from_essay(soup)
        
        return html, iso_date, raw_date

