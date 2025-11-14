"""
Content caching for essay HTML and parsed content.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from .config import CONTENT_CACHE_DIR


class ContentCache:
    """Manages caching of essay content to disk."""
    
    def __init__(self):
        self.cache_dir = CONTENT_CACHE_DIR
    
    def _get_cache_path(self, essay_id: str) -> Path:
        """Get cache file path for an essay."""
        # Use essay_id as filename, replacing slashes
        safe_id = essay_id.replace('/', '_').replace('.html', '')
        return self.cache_dir / f"{safe_id}.json"
    
    def save_essay_content(
        self,
        essay_id: str,
        content_html: str,
        images: List[Tuple[str, bytes]]
    ) -> bool:
        """
        Save essay content to cache.
        
        Args:
            essay_id: Unique identifier for the essay
            content_html: Parsed HTML content
            images: List of (filename, image_data) tuples
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self._get_cache_path(essay_id)
            
            # Convert image data to base64 strings for JSON storage
            images_data = []
            for img_filename, img_bytes in images:
                import base64
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                images_data.append({
                    'filename': img_filename,
                    'data': img_b64
                })
            
            cache_data = {
                'essay_id': essay_id,
                'content_html': content_html,
                'images': images_data
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not cache content for {essay_id}: {e}")
            return False
    
    def load_essay_content(
        self,
        essay_id: str
    ) -> Optional[Tuple[str, List[Tuple[str, bytes]]]]:
        """
        Load essay content from cache.
        
        Args:
            essay_id: Unique identifier for the essay
        
        Returns:
            (content_html, images) tuple if cached, None otherwise
        """
        try:
            cache_path = self._get_cache_path(essay_id)
            
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            content_html = cache_data['content_html']
            
            # Convert base64 strings back to bytes
            images = []
            for img_data in cache_data.get('images', []):
                import base64
                img_filename = img_data['filename']
                img_bytes = base64.b64decode(img_data['data'])
                images.append((img_filename, img_bytes))
            
            return content_html, images
            
        except Exception as e:
            print(f"Warning: Could not load cached content for {essay_id}: {e}")
            return None
    
    def has_cached_content(self, essay_id: str) -> bool:
        """Check if essay content is cached."""
        cache_path = self._get_cache_path(essay_id)
        return cache_path.exists()
    
    def clear_cache(self) -> int:
        """Clear all cached content. Returns number of files deleted."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass
        return count
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached content."""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cached_essays': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

