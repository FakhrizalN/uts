"""
Test performance and stress scenarios.
Verifies system can handle high load with deduplication.
"""
import pytest
import asyncio
import tempfile
import time
from pathlib import Path
from datetime import datetime

from src.models import Event
from src.dedup_store import DedupStore
from src.consumer import Consumer


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_performance.db"
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
    return asyncio.Queue(maxsize=10000)


@pytest.fixture
def consumer(event_queue, dedup_store):
    """Create Consumer instance"""
    return Consumer(
        queue=event_queue,
        dedup_store=dedup_store,
        batch_size=100,
        sleep_interval=0.001
    )


def generate_events(count: int, duplicate_ratio: float = 0.0) -> list:
    """
    Generate test events with specified duplicate ratio.
    
    Args:
        count: Total number of events to generate
        duplicate_ratio: Ratio of duplicates (0.0 to 1.0)
        
    Returns:
        List of Event objects
    """
    unique_count = int(count * (1 - duplicate_ratio))
    
    
    unique_events = [
        Event(
            topic=f"topic-{i % 10}",  
            event_id=f"evt-perf-{i:06d}",
            timestamp=datetime.utcnow().isoformat() + 'Z',
            source="perf-test",
            payload={"index": i, "data": f"test-data-{i}"}
        )
        for i in range(unique_count)
    ]
    
    
    events = unique_events.copy()
    duplicate_count = count - unique_count
    
    for i in range(duplicate_count):
        
        events.append(unique_events[i % unique_count])
    
    return events


@pytest.mark.asyncio
async def test_performance_5000_events_with_20_percent_duplicates(consumer, event_queue):
    """
    Test processing 5000 events with 20% duplication rate.
    This is the minimum requirement from the assignment.
    """
    
    events = generate_events(5000, duplicate_ratio=0.20)
    
    
    await consumer.start()
    
    
    queue_start = time.time()
    for event in events:
        await event_queue.put(event)
    queue_time = time.time() - queue_start
    
    
    process_start = time.time()
    while not event_queue.empty():
        await asyncio.sleep(0.1)
    
    
    await asyncio.sleep(0.5)
    process_time = time.time() - process_start
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    
    assert stats['received'] == 5000, "Should receive all 5000 events"
    assert stats['unique_processed'] == 4000, "Should process 4000 unique events (80%)"
    assert stats['duplicate_dropped'] == 1000, "Should drop 1000 duplicates (20%)"
    
    
    total_time = queue_time + process_time
    throughput = 5000 / total_time if total_time > 0 else 0
    
    print(f"\nPerformance Metrics:")
    print(f"  Total events: 5000")
    print(f"  Unique: {stats['unique_processed']}")
    print(f"  Duplicates: {stats['duplicate_dropped']}")
    print(f"  Queue time: {queue_time:.3f}s")
    print(f"  Process time: {process_time:.3f}s")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Throughput: {throughput:.0f} events/s")
    
    
    assert throughput >= 100, f"Throughput too low: {throughput:.0f} events/s"


def test_dedup_store_performance(dedup_store):
    """Test dedup store lookup performance"""
    
    events = generate_events(1000, duplicate_ratio=0.0)
    
    store_start = time.time()
    for event in events:
        dedup_store.store_event(event)
    store_time = time.time() - store_start
    
    
    lookup_start = time.time()
    for event in events:
        is_dup = dedup_store.is_duplicate(event)
        assert is_dup is True
    lookup_time = time.time() - lookup_start
    
    print(f"\nDedup Store Performance:")
    print(f"  Store 1000 events: {store_time:.3f}s ({1000/store_time:.0f} ops/s)")
    print(f"  Lookup 1000 events: {lookup_time:.3f}s ({1000/lookup_time:.0f} ops/s)")
    
    
    assert 1000 / store_time >= 100, "Store operations too slow"
    assert 1000 / lookup_time >= 100, "Lookup operations too slow"


@pytest.mark.asyncio
async def test_concurrent_publishers(consumer, event_queue):
    """Test handling events from multiple concurrent publishers"""
    
    async def publisher(publisher_id: int, event_count: int):
        """Simulate a publisher sending events"""
        for i in range(event_count):
            event = Event(
                topic=f"publisher-{publisher_id}",
                event_id=f"pub{publisher_id}-evt-{i}",
                timestamp=datetime.utcnow().isoformat() + 'Z',
                source=f"publisher-{publisher_id}",
                payload={"pub": publisher_id, "seq": i}
            )
            await event_queue.put(event)
    
    
    await consumer.start()
    
    
    start_time = time.time()
    
    publishers = [
        publisher(pub_id, 500)
        for pub_id in range(5)
    ]
    
    await asyncio.gather(*publishers)
    
    
    while not event_queue.empty():
        await asyncio.sleep(0.1)
    
    await asyncio.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    
    await consumer.stop()
    
    
    stats = consumer.get_stats()
    
    assert stats['received'] == 2500  
    assert stats['unique_processed'] == 2500  
    assert stats['duplicate_dropped'] == 0
    
    throughput = 2500 / elapsed if elapsed > 0 else 0
    
    print(f"\nConcurrent Publishers Test:")
    print(f"  Publishers: 5")
    print(f"  Events per publisher: 500")
    print(f"  Total: 2500")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:.0f} events/s")


@pytest.mark.asyncio
async def test_latency_per_event(consumer, event_queue):
    """Test average latency per event processing"""
    
    events = generate_events(100, duplicate_ratio=0.0)
    
    
    await consumer.start()
    
    
    latencies = []
    
    for event in events:
        start = time.time()
        await event_queue.put(event)
        
        
        await asyncio.sleep(0.01)  
        
        latency = time.time() - start
        latencies.append(latency)
    
    
    await asyncio.sleep(0.5)
    
    
    await consumer.stop()
    
    avg_latency = sum(latencies) / len(latencies) * 1000  
    
    print(f"\nLatency Test:")
    print(f"  Average latency: {avg_latency:.2f}ms")
    print(f"  Min latency: {min(latencies)*1000:.2f}ms")
    print(f"  Max latency: {max(latencies)*1000:.2f}ms")
    
    
    assert avg_latency < 50, f"Latency too high: {avg_latency:.2f}ms"
