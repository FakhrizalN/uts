"""
Manual testing script for the API endpoints.
Demonstrates publishing events, querying, and checking stats.
"""
import requests
import json
import time
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8080"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def health_check():
    """Check if service is healthy"""
    print_section("Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def publish_event(topic, event_id=None, payload=None):
    """Publish a single event"""
    if event_id is None:
        event_id = f"evt-{uuid.uuid4().hex[:16]}"
    
    if payload is None:
        payload = {"test": "data", "timestamp": time.time()}
    
    event = {
        "topic": topic,
        "event_id": event_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "source": "manual-test",
        "payload": payload
    }
    
    response = requests.post(f"{BASE_URL}/publish", json=event)
    print(f"Published event {event_id} to topic '{topic}'")
    print(f"Response: {response.json()}")
    return event_id


def publish_batch(topic, count=10):
    """Publish a batch of events"""
    print_section(f"Publishing Batch of {count} Events")
    
    events = [
        {
            "topic": topic,
            "event_id": f"evt-batch-{i:04d}",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "source": "manual-test",
            "payload": {"index": i, "batch": True}
        }
        for i in range(count)
    ]
    
    response = requests.post(f"{BASE_URL}/publish", json=events)
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def simulate_duplicates(topic, event_id):
    """Simulate duplicate event submissions"""
    print_section("Simulating Duplicate Events")
    
    # Send same event 5 times
    for i in range(5):
        publish_event(topic, event_id, {"attempt": i})
        time.sleep(0.1)


def query_events(topic=None, limit=10):
    """Query events from the aggregator"""
    print_section(f"Querying Events (topic={topic}, limit={limit})")
    
    params = {"limit": limit}
    if topic:
        params["topic"] = topic
    
    response = requests.get(f"{BASE_URL}/events", params=params)
    data = response.json()
    
    print(f"Total events: {data['total']}")
    if data.get('filtered_by_topic'):
        print(f"Filtered by topic: {data['filtered_by_topic']}")
    
    print("\nEvents:")
    for event in data['events'][:5]:  # Show first 5
        print(f"  - {event['topic']}:{event['event_id']} @ {event['processed_at']}")
    
    if len(data['events']) > 5:
        print(f"  ... and {len(data['events']) - 5} more")


def get_stats():
    """Get aggregator statistics"""
    print_section("Statistics")
    
    response = requests.get(f"{BASE_URL}/stats")
    data = response.json()
    
    print(f"Received: {data['received']}")
    print(f"Unique Processed: {data['unique_processed']}")
    print(f"Duplicates Dropped: {data['duplicate_dropped']}")
    print(f"Topics: {', '.join(data['topics'])}")
    print(f"Uptime: {data['uptime_seconds']:.1f} seconds")
    print(f"Started at: {data['started_at']}")


def main():
    """Run complete test scenario"""
    print_section("UTS Log Aggregator - Manual Testing")
    
    # 1. Health check
    if not health_check():
        print("Service is not healthy. Exiting.")
        return
    
    time.sleep(0.5)
    
    # 2. Publish single events
    print_section("Publishing Single Events")
    event_id_1 = publish_event("user-activity", payload={"action": "login", "user": "alice"})
    time.sleep(0.1)
    publish_event("user-activity", payload={"action": "logout", "user": "bob"})
    time.sleep(0.1)
    publish_event("system-log", payload={"level": "INFO", "message": "Service started"})
    
    time.sleep(0.5)
    
    # 3. Simulate duplicates
    simulate_duplicates("user-activity", event_id_1)
    
    time.sleep(0.5)
    
    # 4. Publish batch
    publish_batch("transaction", count=20)
    
    time.sleep(1)  # Wait for processing
    
    # 5. Query events
    query_events()
    time.sleep(0.5)
    
    query_events(topic="user-activity")
    time.sleep(0.5)
    
    # 6. Get statistics
    get_stats()
    
    print_section("Testing Complete")
    print("\nKey Observations:")
    print("1. Check that duplicate_dropped > 0 (deduplication working)")
    print("2. Verify unique_processed = received - duplicate_dropped")
    print("3. Confirm events are queryable by topic")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\nError: Cannot connect to service at", BASE_URL)
        print("Make sure the service is running:")
        print("  python -m src.main")
        print("  OR")
        print("  docker run -p 8080:8080 uts-aggregator")
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
