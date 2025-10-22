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
    # Phase 1: Store events in first instance
    store1 = DedupStore(temp_db)
    
    for event in sample_events[:3]:
        result = store1.store_event(event)
        assert result is True, "First store should succeed"
    
    # Verify stats in first instance
    unique_count1, topics1 = store1.get_stats()
    assert unique_count1 == 3
    
    # Simulate restart by creating new store instance with same DB
    store2 = DedupStore(temp_db)
    
    # Phase 2: Try to store same events again
    for event in sample_events[:3]:
        result = store2.store_event(event)
        assert result is False, "Events should be detected as duplicates after restart"
    
    # Verify stats in second instance
    unique_count2, topics2 = store2.get_stats()
    assert unique_count2 == 3, "Unique count should remain 3"
    
    # Store new events
    for event in sample_events[3:]:
        result = store2.store_event(event)
        assert result is True, "New events should be stored"
    
    # Verify final stats
    unique_count3, topics3 = store2.get_stats()
    assert unique_count3 == 5, "Should have 5 total unique events"


def test_persistence_is_duplicate_check(temp_db, sample_events):
    """Test that is_duplicate works correctly after restart"""
    # Store events in first instance
    store1 = DedupStore(temp_db)
    for event in sample_events[:3]:
        store1.store_event(event)
    
    # Create new instance (simulate restart)
    store2 = DedupStore(temp_db)
    
    # Check duplicates
    for event in sample_events[:3]:
        assert store2.is_duplicate(event) is True
    
    # Check non-duplicates
    for event in sample_events[3:]:
        assert store2.is_duplicate(event) is False


def test_persistence_get_events_after_restart(temp_db, sample_events):
    """Test that get_events returns correct data after restart"""
    # Store events in first instance
    store1 = DedupStore(temp_db)
    for event in sample_events:
        store1.store_event(event)
    
    # Create new instance (simulate restart)
    store2 = DedupStore(temp_db)
    
    # Retrieve events
    retrieved = store2.get_events(topic="persistent-topic", limit=100)
    
    # Verify all events are retrieved
    assert len(retrieved) == 5
    
    # Verify event data
    event_ids = {evt.event_id for evt in retrieved}
    expected_ids = {f"evt-persist-{i}" for i in range(5)}
    assert event_ids == expected_ids


def test_persistence_topics_after_restart(temp_db):
    """Test that topics are correctly retrieved after restart"""
    # Create events with multiple topics
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
    
    # Store in first instance
    store1 = DedupStore(temp_db)
    for event in events:
        store1.store_event(event)
    
    # Create new instance (simulate restart)
    store2 = DedupStore(temp_db)
    
    # Get stats
    unique_count, topics = store2.get_stats()
    
    # Verify topics
    assert len(topics) == 3
    assert set(topics) == {"topic-0", "topic-1", "topic-2"}


def test_persistence_multiple_restarts(temp_db, sample_events):
    """Test persistence across multiple restart cycles"""
    events_per_cycle = 2
    
    for cycle in range(3):
        # Create new store instance (simulating restart)
        store = DedupStore(temp_db)
        
        # Store new events for this cycle
        start_idx = cycle * events_per_cycle
        end_idx = start_idx + events_per_cycle
        
        for event in sample_events[start_idx:end_idx]:
            result = store.store_event(event)
            assert result is True, f"New event in cycle {cycle} should be stored"
        
        # Verify all previous events are still duplicates
        for prev_cycle in range(cycle + 1):
            prev_start = prev_cycle * events_per_cycle
            prev_end = prev_start + events_per_cycle
            
            for event in sample_events[prev_start:prev_end]:
                assert store.is_duplicate(event) is True, \
                    f"Event from cycle {prev_cycle} should be duplicate in cycle {cycle}"
    
    # Final verification
    final_store = DedupStore(temp_db)
    unique_count, _ = final_store.get_stats()
    assert unique_count == 5, "Should have 5 unique events after all cycles"


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
    
    # Store first event
    store1 = DedupStore(temp_db)
    result1 = store1.store_event(event1)
    assert result1 is True
    
    # Simulate restart and try to store event with different payload
    store2 = DedupStore(temp_db)
    result2 = store2.store_event(event2)
    assert result2 is False, "Should be duplicate despite different payload"
    
    # Verify only one event stored
    unique_count, _ = store2.get_stats()
    assert unique_count == 1
