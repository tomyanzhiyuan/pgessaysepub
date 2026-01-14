"""Tests for the StateManager module."""

import pytest
import json
import tempfile
from pathlib import Path
from dataclasses import asdict
from pg_epub.state import StateManager, EssayState


class TestEssayState:
    """Tests for EssayState dataclass."""

    def test_create_essay_state(self):
        """Test creating an EssayState instance."""
        state = EssayState(
            essay_id="test.html",
            title="Test Essay",
            url="http://paulgraham.com/test.html"
        )
        assert state.essay_id == "test.html"
        assert state.title == "Test Essay"
        assert state.read is False  # Default

    def test_essay_state_to_dict(self):
        """Test converting EssayState to dictionary using asdict."""
        state = EssayState(
            essay_id="test.html",
            title="Test Essay",
            url="http://paulgraham.com/test.html",
            date="2024-01-15",
            read=True
        )
        d = asdict(state)
        assert d["essay_id"] == "test.html"
        assert d["read"] is True
        assert d["date"] == "2024-01-15"


class TestStateManager:
    """Tests for StateManager class."""

    @pytest.fixture
    def temp_state_file(self, tmp_path):
        """Create a temporary state file path."""
        return tmp_path / "state.json"

    def test_update_essay_new(self, temp_state_file):
        """Test adding a new essay."""
        manager = StateManager(state_file=temp_state_file)
        
        essay = manager.update_essay(
            essay_id="new.html",
            title="New Essay",
            url="http://paulgraham.com/new.html"
        )
        
        assert essay.essay_id == "new.html"
        assert "new.html" in manager.essays
        assert manager.essays["new.html"].read is False

    def test_update_essay_existing(self, temp_state_file):
        """Test updating an existing essay."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("test.html", "Test", "http://x/test.html")
        
        # Update with new title
        manager.update_essay("test.html", "Updated Title", "http://x/test.html")
        
        assert manager.essays["test.html"].title == "Updated Title"

    def test_mark_read(self, temp_state_file):
        """Test marking essays as read."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("a.html", "A", "http://x/a.html")
        manager.update_essay("b.html", "B", "http://x/b.html")
        
        count = manager.mark_read(["a.html", "b.html"])
        
        assert count == 2
        assert manager.essays["a.html"].read is True
        assert manager.essays["b.html"].read is True

    def test_mark_unread(self, temp_state_file):
        """Test marking essays as unread."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("test.html", "Test", "http://x/test.html", read=True)
        
        count = manager.mark_unread(["test.html"])
        
        assert count == 1
        assert manager.essays["test.html"].read is False

    def test_get_unread_essays(self, temp_state_file):
        """Test getting list of unread essays."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("a.html", "Essay A", "http://x/a.html")
        manager.update_essay("b.html", "Essay B", "http://x/b.html")
        manager.mark_read(["a.html"])
        
        unread = manager.get_unread_essays()
        
        assert len(unread) == 1
        assert unread[0].essay_id == "b.html"

    def test_get_read_essays(self, temp_state_file):
        """Test getting list of read essays."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("a.html", "Essay A", "http://x/a.html")
        manager.update_essay("b.html", "Essay B", "http://x/b.html")
        manager.mark_read(["a.html"])
        
        read = manager.get_read_essays()
        
        assert len(read) == 1
        assert read[0].essay_id == "a.html"

    def test_find_essays_by_title(self, temp_state_file):
        """Test finding essays by partial title match."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("avg.html", "Beating the Averages", "http://x/avg.html")
        manager.update_essay("work.html", "How to Work Hard", "http://x/work.html")
        
        results = manager.find_essays_by_title("averages")
        
        assert len(results) == 1
        assert "avg.html" in results

    def test_persistence(self, temp_state_file):
        """Test that state persists across instances."""
        # First instance
        manager1 = StateManager(state_file=temp_state_file)
        manager1.update_essay("test.html", "Test", "http://x/test.html")
        manager1.mark_read(["test.html"])
        manager1.save()
        
        # Second instance
        manager2 = StateManager(state_file=temp_state_file)
        
        assert "test.html" in manager2.essays
        assert manager2.essays["test.html"].read is True

    def test_reset(self, temp_state_file):
        """Test resetting all state."""
        manager = StateManager(state_file=temp_state_file)
        manager.update_essay("test.html", "Test", "http://x/test.html")
        manager.save()
        
        manager.reset()
        
        assert len(manager.essays) == 0
        assert not temp_state_file.exists()
