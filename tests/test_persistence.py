"""
Test persistence after restart.
Verifies that dedup store maintains state after restart simulation.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from src.models import Event
from src.dedup_store import DedupStore


@pytest.fixture
def temp_db():
    """Create temporary database that persists across store instances"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_persistence.db"
        yield db_path


@pytest.fixture
def sample_events():
    """Create sample events for testing"""
    base_time = datetime.utcnow()
    return [
        Event(
            topic="persistent-topic",
            event_id=f"evt-persist-{i}",
            timestamp=base_time.isoformat() + 'Z',
            source="test",
            payload={"index": i}
        )
        for i in range(5)
    ]


def test_persistence_after_restart(temp_db, sample_events):
    """Test that dedup store maintains state after restart"""
    
    store1 = DedupStore(temp_db)
    
    for event in sample_events[:3]:
        result = store1.store_event(event)
        assert result is True, "First store should succeed"
    
    
    stats = store1.get_stats()
    unique_count = stats["unique_processed"]
    topics = stats["topics"]
    assert unique_count == 3
    
    store1.close()  # Close connection before creating new instance
    
    store2 = DedupStore(temp_db)
    
    
    for event in sample_events[:3]:
        result = store2.store_event(event)
        assert result is False, "Events should be detected as duplicates after restart"
    
    
    stats = store2.get_stats()
    unique_count = stats["unique_processed"]
    topics = stats["topics"]
    assert unique_count == 3, "Unique count should remain 3"
    
    
    for event in sample_events[3:]:
        result = store2.store_event(event)
        assert result is True, "New events should be stored"
    
    
    stats = store2.get_stats()
    unique_count = stats["unique_processed"]
    topics = stats["topics"]
    assert unique_count == 5, "Should have 5 total unique events"
    
    store2.close()  # Close connection at end


def test_persistence_is_duplicate_check(temp_db, sample_events):
    """Test that is_duplicate works correctly after restart"""
    
    store1 = DedupStore(temp_db)
    for event in sample_events[:3]:
        store1.store_event(event)
    
    store1.close()  # Close before restart
    
    store2 = DedupStore(temp_db)
    
    
    for event in sample_events[:3]:
        assert store2.is_duplicate(event) is True
    
    
    for event in sample_events[3:]:
        assert store2.is_duplicate(event) is False
    
    store2.close()  # Close at end


def test_persistence_get_events_after_restart(temp_db, sample_events):
    """Test that get_events returns correct data after restart"""
    
    store1 = DedupStore(temp_db)
    for event in sample_events:
        store1.store_event(event)
    
    store1.close()  # Close before restart
    
    
    store2 = DedupStore(temp_db)
    
    
    retrieved = store2.get_events(topic="persistent-topic", limit=100)
    
    
    assert len(retrieved) == 5
    
    
    event_ids = {evt.event_id for evt in retrieved}
    expected_ids = {f"evt-persist-{i}" for i in range(5)}
    assert event_ids == expected_ids
    
    store2.close()  # Close at end


def test_persistence_topics_after_restart(temp_db):
    """Test that topics are correctly retrieved after restart"""
    
    events = [
        Event(
            topic=f"topic-{i}",
            event_id=f"evt-{i}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source="test",
            payload={}
        )
        for i in range(3)
    ]
    
    
    store1 = DedupStore(temp_db)
    for event in events:
        store1.store_event(event)
    
    store1.close()  # Close before restart
    
    store2 = DedupStore(temp_db)
    
    
    stats = store2.get_stats()
    topics = stats["topics"]
    
    
    assert len(topics) == 3
    assert set(topics) == {"topic-0", "topic-1", "topic-2"}
    
    store2.close()  # Close at end


def test_persistence_multiple_restarts(temp_db, sample_events):
    """Test persistence across multiple restart cycles"""
    events_per_cycle = 2
    
    for cycle in range(3):
        
        store = DedupStore(temp_db)
        
        
        start_idx = cycle * events_per_cycle
        end_idx = start_idx + events_per_cycle
        
        for event in sample_events[start_idx:end_idx]:
            result = store.store_event(event)
            assert result is True, f"New event in cycle {cycle} should be stored"
        
        
        for prev_cycle in range(cycle + 1):
            prev_start = prev_cycle * events_per_cycle
            prev_end = prev_start + events_per_cycle
            
            for event in sample_events[prev_start:prev_end]:
                assert store.is_duplicate(event) is True, \
                    f"Event from cycle {prev_cycle} should be duplicate in cycle {cycle}"
        
        store.close()  # Close after each cycle
    
    
    final_store = DedupStore(temp_db)
    stats = final_store.get_stats()
    unique_count = stats["unique_processed"]
    assert unique_count == 5, "Should have 5 unique events after all cycles"
    
    final_store.close()  # Close at end


def test_persistence_with_payload_changes(temp_db):
    """Test that events with same topic/event_id but different payload are still duplicates"""
    event1 = Event(
        topic="test",
        event_id="evt-same",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={"data": "original"}
    )
    
    event2 = Event(
        topic="test",
        event_id="evt-same",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={"data": "modified", "extra": "field"}
    )
    
    
    store1 = DedupStore(temp_db)
    result1 = store1.store_event(event1)
    assert result1 is True
    
    store1.close()  # Close before restart
    
    store2 = DedupStore(temp_db)
    result2 = store2.store_event(event2)
    assert result2 is False, "Should be duplicate despite different payload"
    
    
    stats = store2.get_stats()
    unique_count = stats["unique_processed"]
    assert unique_count == 1
    
    store2.close()  # Close at end
