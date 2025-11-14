"""
State management for tracking read/unread essays and caching metadata.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from .config import STATE_FILE


@dataclass
class EssayState:
    """State information for a single essay."""
    essay_id: str
    title: str
    url: str
    date: Optional[str] = None  # ISO format YYYY-MM-DD
    raw_date_str: Optional[str] = None
    read: bool = False
    last_seen: Optional[str] = None  # ISO timestamp


class StateManager:
    """Manages read/unread state and essay metadata."""
    
    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.essays: Dict[str, EssayState] = {}
        self.last_update: Optional[str] = None
        self.load()
    
    def load(self) -> None:
        """Load state from JSON file."""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.last_update = data.get('last_update')
            
            for essay_id, essay_data in data.get('essays', {}).items():
                self.essays[essay_id] = EssayState(
                    essay_id=essay_id,
                    title=essay_data.get('title', ''),
                    url=essay_data.get('url', ''),
                    date=essay_data.get('date'),
                    raw_date_str=essay_data.get('raw_date_str'),
                    read=essay_data.get('read', False),
                    last_seen=essay_data.get('last_seen')
                )
        except Exception as e:
            print(f"Warning: Could not load state file: {e}")
            self.essays = {}
    
    def save(self) -> None:
        """Save state to JSON file."""
        data = {
            'last_update': datetime.now().isoformat(),
            'essays': {
                essay_id: asdict(essay)
                for essay_id, essay in self.essays.items()
            }
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def update_essay(
        self,
        essay_id: str,
        title: str,
        url: str,
        date: Optional[str] = None,
        raw_date_str: Optional[str] = None,
        read: Optional[bool] = None
    ) -> EssayState:
        """Update or create an essay's state."""
        if essay_id in self.essays:
            essay = self.essays[essay_id]
            essay.title = title
            essay.url = url
            if date is not None:
                essay.date = date
            if raw_date_str is not None:
                essay.raw_date_str = raw_date_str
            if read is not None:
                essay.read = read
            essay.last_seen = datetime.now().isoformat()
        else:
            # New essay - default to unread
            essay = EssayState(
                essay_id=essay_id,
                title=title,
                url=url,
                date=date,
                raw_date_str=raw_date_str,
                read=False if read is None else read,
                last_seen=datetime.now().isoformat()
            )
            self.essays[essay_id] = essay
        
        return essay
    
    def mark_read(self, essay_ids: List[str]) -> int:
        """Mark essays as read. Returns count of essays marked."""
        count = 0
        for essay_id in essay_ids:
            if essay_id in self.essays:
                self.essays[essay_id].read = True
                count += 1
        return count
    
    def mark_unread(self, essay_ids: List[str]) -> int:
        """Mark essays as unread. Returns count of essays marked."""
        count = 0
        for essay_id in essay_ids:
            if essay_id in self.essays:
                self.essays[essay_id].read = False
                count += 1
        return count
    
    def find_essays_by_title(self, title_query: str) -> List[str]:
        """Find essay IDs by partial title match (case-insensitive)."""
        title_lower = title_query.lower()
        return [
            essay_id
            for essay_id, essay in self.essays.items()
            if title_lower in essay.title.lower()
        ]
    
    def get_essay(self, essay_id: str) -> Optional[EssayState]:
        """Get essay state by ID."""
        return self.essays.get(essay_id)
    
    def get_all_essays(self) -> List[EssayState]:
        """Get all essays."""
        return list(self.essays.values())
    
    def get_unread_essays(self) -> List[EssayState]:
        """Get all unread essays."""
        return [e for e in self.essays.values() if not e.read]
    
    def get_read_essays(self) -> List[EssayState]:
        """Get all read essays."""
        return [e for e in self.essays.values() if e.read]
    
    def reset(self) -> None:
        """Clear all state."""
        self.essays = {}
        self.last_update = None
        if self.state_file.exists():
            self.state_file.unlink()

