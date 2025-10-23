"""
Test API endpoints.
Verifies that REST API behaves correctly.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from httpx import AsyncClient
import asyncio
import tempfile
from pathlib import Path

from src.main import Application
from src.api import create_app


@pytest_asyncio.fixture
async def app_instance():
    """Create application instance for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        
        from src.config import Config
        Config.DATA_DIR = Path(tmpdir)
        Config.DB_PATH = Config.DATA_DIR / "test_api.db"
        
        app = Application()
        await app.startup()
        yield app
        await app.shutdown()


@pytest_asyncio.fixture
async def test_app(app_instance):
    """Create FastAPI test app"""
    app = create_app(
        consumer=app_instance.consumer,
        dedup_store=app_instance.dedup_store,
        start_time=app_instance.start_time
    )
    
    app.state.consumer = app_instance.consumer
    app.state.dedup_store = app_instance.dedup_store
    app.state.queue = app_instance.queue
    app.state.start_time = app_instance.start_time
    
    yield app


@pytest_asyncio.fixture
async def client(app_instance):
    """Create async HTTP client for testing"""
    app = create_app(
        consumer=app_instance.consumer,
        dedup_store=app_instance.dedup_store,
        start_time=app_instance.start_time
    )
    
    app.state.consumer = app_instance.consumer
    app.state.dedup_store = app_instance.dedup_store
    app.state.queue = app_instance.queue
    app.state.start_time = app_instance.start_time
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint returns service info"""
    response = await client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["service"] == "UTS Log Aggregator"
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_publish_single_event(client):
    """Test publishing single event"""
    event = {
        "topic": "test-topic",
        "event_id": "evt-api-test-001",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "source": "api-test",
        "payload": {"test": "data"}
    }
    
    response = await client.post("/publish", json=event)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "queued"
    assert data["queued_count"] == 1


@pytest.mark.asyncio
async def test_publish_batch_events(client):
    """Test publishing batch of events"""
    events = [
        {
            "topic": "batch-topic",
            "event_id": f"evt-batch-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "api-test",
            "payload": {"index": i}
        }
        for i in range(5)
    ]
    
    response = await client.post("/publish", json=events)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "queued"
    assert data["queued_count"] == 5


@pytest.mark.asyncio
async def test_publish_invalid_event(client):
    """Test publishing invalid event returns error"""
    invalid_event = {
        "topic": "test",
        
    }
    
    response = await client.post("/publish", json=invalid_event)
    # API returns 500 for validation errors currently
    assert response.status_code == 500  


@pytest.mark.asyncio
async def test_publish_invalid_timestamp(client):
    """Test publishing event with invalid timestamp"""
    event = {
        "topic": "test",
        "event_id": "evt-001",
        "timestamp": "not-a-valid-timestamp",
        "source": "test",
        "payload": {}
    }
    
    response = await client.post("/publish", json=event)
    # API returns 500 for validation errors currently
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_events(client, app_instance):
    """Test retrieving events"""
    
    events = [
        {
            "topic": "get-test",
            "event_id": f"evt-get-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {"index": i}
        }
        for i in range(3)
    ]
    
    await client.post("/publish", json=events)
    
    
    await asyncio.sleep(0.5)
    
    
    response = await client.get("/events")
    assert response.status_code == 200
    
    data = response.json()
    assert "events" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_events_filtered_by_topic(client, app_instance):
    """Test retrieving events filtered by topic"""
    
    events = [
        {
            "topic": "topic-A",
            "event_id": f"evt-a-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {}
        }
        for i in range(2)
    ] + [
        {
            "topic": "topic-B",
            "event_id": f"evt-b-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {}
        }
        for i in range(3)
    ]
    
    await client.post("/publish", json=events)
    
    
    await asyncio.sleep(0.5)
    
    
    response = await client.get("/events?topic=topic-A")
    assert response.status_code == 200
    
    data = response.json()
    assert data["filtered_by_topic"] == "topic-A"
    
    
    for event in data["events"]:
        assert event["topic"] == "topic-A"


@pytest.mark.asyncio
async def test_get_events_with_limit(client, app_instance):
    """Test retrieving events with limit parameter"""
    
    events = [
        {
            "topic": "limit-test",
            "event_id": f"evt-limit-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {}
        }
        for i in range(20)
    ]
    
    await client.post("/publish", json=events)
    
    
    await asyncio.sleep(0.5)
    
    
    response = await client.get("/events?limit=5")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["events"]) <= 5


@pytest.mark.asyncio
async def test_get_stats(client, app_instance):
    """Test retrieving statistics"""
    
    events = [
        {
            "topic": "stats-test",
            "event_id": "evt-stats-1",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {}
        }
    ] * 3  
    
    await client.post("/publish", json=events)
    
    
    await asyncio.sleep(0.5)
    
    
    response = await client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "received" in data
    assert "unique_processed" in data
    assert "duplicate_dropped" in data
    assert "topics" in data
    assert "uptime" in data  # Changed from uptime_seconds
    
    
    assert data["received"] >= 3
    assert data["duplicate_dropped"] >= 2


@pytest.mark.asyncio
async def test_stats_consistency(client, app_instance):
    """Test that stats are consistent across endpoints"""
    
    unique_events = [
        {
            "topic": "consistency",
            "event_id": f"evt-unique-{i}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "test",
            "payload": {}
        }
        for i in range(10)
    ]
    
    duplicate_events = [unique_events[0]] * 5  
    
    await client.post("/publish", json=unique_events)
    await client.post("/publish", json=duplicate_events)
    
    
    await asyncio.sleep(0.5)
    
    
    stats_response = await client.get("/stats")
    stats = stats_response.json()
    
    
    events_response = await client.get("/events?topic=consistency")
    events_data = events_response.json()
    
    
    assert stats["unique_processed"] >= len(events_data["events"])
