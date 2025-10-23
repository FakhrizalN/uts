"""
Test idempotency behavior.
Verifies that consumer processes each unique event exactly once.
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

from src.models import Event
from src.dedup_store import DedupStore
from src.consumer import Consumer


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_idempotency.db"
        yield db_path


@pytest.fixture
def dedup_store(temp_db):
    """Create DedupStore instance"""
    store = DedupStore(temp_db)
    yield store
    # Close connection before cleanup
    store.close()


@pytest.fixture
def event_queue():
    """Create asyncio queue for events"""
    return asyncio.Queue()


@pytest.fixture
def consumer(event_queue, dedup_store):
    """Create Consumer instance"""
    return Consumer(
        queue=event_queue,
        dedup_store=dedup_store,
        batch_size=10,
        sleep_interval=0.01
    )


@pytest.fixture
def sample_events():
    """Create sample events for testing"""
    base_time = datetime.utcnow()
    return [
        Event(
            topic="test",
            event_id=f"evt-{i}",
            timestamp=base_time.isoformat() + 'Z',
            source="test",
            payload={"index": i}
        )
        for i in range(10)
    ]


@pytest.mark.asyncio
async def test_consumer_processes_unique_events(consumer, event_queue, sample_events):
    """Test that consumer processes all unique events"""
    
    await consumer.start()
    
    
    for event in sample_events:
        await event_queue.put(event)
    
    
    await asyncio.sleep(0.5)
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    assert stats['received'] == 10
    assert stats['unique_processed'] == 10
    assert stats['duplicate_dropped'] == 0


@pytest.mark.asyncio
async def test_consumer_drops_duplicates(consumer, event_queue, sample_events):
    """Test that consumer drops duplicate events"""
    
    await consumer.start()
    
    
    for event in sample_events[:5]:
        await event_queue.put(event)
    
    
    for event in sample_events[:3]:
        await event_queue.put(event)
    
    
    await asyncio.sleep(0.5)
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    assert stats['received'] == 8  
    assert stats['unique_processed'] == 5  
    assert stats['duplicate_dropped'] == 3  


@pytest.mark.asyncio
async def test_idempotency_with_interleaved_duplicates(consumer, event_queue):
    """Test idempotency with duplicates interleaved with unique events"""
    
    await consumer.start()
    
    
    evt1 = Event(
        topic="test",
        event_id="evt-1",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={"data": 1}
    )
    evt2 = Event(
        topic="test",
        event_id="evt-2",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={"data": 2}
    )
    
    
    await event_queue.put(evt1)
    await event_queue.put(evt2)
    await event_queue.put(evt1)
    await event_queue.put(evt2)
    await event_queue.put(evt1)
    
    
    await asyncio.sleep(0.5)
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    assert stats['received'] == 5
    assert stats['unique_processed'] == 2
    assert stats['duplicate_dropped'] == 3


@pytest.mark.asyncio
async def test_consumer_graceful_stop_processes_remaining(consumer, event_queue, sample_events):
    """Test that stopping consumer processes remaining queued events"""
    
    for event in sample_events[:5]:
        await event_queue.put(event)
    
    
    await consumer.start()
    await asyncio.sleep(0.2)  
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    assert stats['received'] == 5
    assert stats['unique_processed'] == 5


@pytest.mark.asyncio
async def test_consumer_handles_same_event_id_different_topics(consumer, event_queue):
    """Test that same event_id in different topics are treated as different events"""
    
    await consumer.start()
    
    
    evt1 = Event(
        topic="topic-A",
        event_id="evt-same-id",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={}
    )
    evt2 = Event(
        topic="topic-B",
        event_id="evt-same-id",
        timestamp=datetime.utcnow().isoformat() + 'Z',
        source="test",
        payload={}
    )
    
    
    await event_queue.put(evt1)
    await event_queue.put(evt2)
    
    
    await asyncio.sleep(0.3)
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    assert stats['unique_processed'] == 2
    assert stats['duplicate_dropped'] == 0
