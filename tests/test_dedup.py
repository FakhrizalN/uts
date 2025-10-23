"""
Test deduplication logic.
Verifies that duplicate events are correctly identified and dropped.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.models import Event
from src.dedup_store import DedupStore


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_dedup.db"
        yield db_path


@pytest.fixture
def dedup_store(temp_db):
    """Create DedupStore instance with temporary database"""
    store = DedupStore(temp_db)
    yield store
    # Close connection before cleanup
    store.close()


@pytest.fixture
def sample_event():
    """Create a sample event for testing"""
    return Event(
        topic="test-topic",
        event_id="evt-12345-abcde",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test-source",
        payload={"test": "data", "value": 123}
    )


def test_store_new_event(dedup_store, sample_event):
    """Test storing a new event returns True"""
    result = dedup_store.store_event(sample_event)
    assert result is True


def test_store_duplicate_event(dedup_store, sample_event):
    """Test storing duplicate event returns False"""
    
    result1 = dedup_store.store_event(sample_event)
    assert result1 is True
    
    
    result2 = dedup_store.store_event(sample_event)
    assert result2 is False


def test_is_duplicate_detection(dedup_store, sample_event):
    """Test duplicate detection method"""
    
    assert dedup_store.is_duplicate(sample_event) is False
    
    
    dedup_store.store_event(sample_event)
    assert dedup_store.is_duplicate(sample_event) is True


def test_different_topics_not_duplicate(dedup_store, sample_event):
    """Test that same event_id in different topics are not duplicates"""
    
    dedup_store.store_event(sample_event)
    
    
    different_topic_event = Event(
        topic="different-topic",
        event_id=sample_event.event_id,
        timestamp=sample_event.timestamp,
        source=sample_event.source,
        payload=sample_event.payload
    )
    
    
    assert dedup_store.is_duplicate(different_topic_event) is False
    result = dedup_store.store_event(different_topic_event)
    assert result is True


def test_same_topic_different_event_id_not_duplicate(dedup_store, sample_event):
    """Test that different event_ids in same topic are not duplicates"""
    
    dedup_store.store_event(sample_event)
    
    
    different_event = Event(
        topic=sample_event.topic,
        event_id="evt-different-67890",
        timestamp=sample_event.timestamp,
        source=sample_event.source,
        payload=sample_event.payload
    )
    
    
    assert dedup_store.is_duplicate(different_event) is False
    result = dedup_store.store_event(different_event)
    assert result is True


def test_multiple_duplicates(dedup_store, sample_event):
    """Test handling multiple duplicate submissions"""
    
    result1 = dedup_store.store_event(sample_event)
    assert result1 is True
    
    
    for i in range(5):
        result = dedup_store.store_event(sample_event)
        assert result is False, f"Duplicate {i+1} should return False"


def test_get_stats_after_dedup(dedup_store, sample_event):
    """Test statistics after storing with duplicates"""
    
    event1 = sample_event
    event2 = Event(
        topic="topic2",
        event_id="evt-2",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="source",
        payload={}
    )
    event3 = Event(
        topic="topic3",
        event_id="evt-3",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="source",
        payload={}
    )
    
    dedup_store.store_event(event1)  
    dedup_store.store_event(event2)  
    dedup_store.store_event(event1)  
    dedup_store.store_event(event3)  
    dedup_store.store_event(event2)  
    
    stats = dedup_store.get_stats()
    unique_count = stats["unique_processed"]
    topics = stats["topics"]
    
    
    assert unique_count == 3
    
    
    assert len(topics) == 3
    assert set(topics) == {"test-topic", "topic2", "topic3"}
