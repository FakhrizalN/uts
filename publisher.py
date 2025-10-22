"""
Publisher simulator for testing (BONUS component for Docker Compose).
Simulates multiple publishers sending events with configurable duplicate rate.
"""
import os
import time
import random
import uuid
import requests
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
AGGREGATOR_URL = os.getenv("AGGREGATOR_URL", "http://localhost:8080")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "1"))
DUPLICATE_RATE = float(os.getenv("DUPLICATE_RATE", "0.20"))

# Topics to use
TOPICS = [
    "user-activity",
    "system-log",
    "transaction",
    "security-event",
    "performance-metric"
]

# Sources to simulate
SOURCES = [
    "web-app",
    "mobile-app",
    "backend-api",
    "cron-job",
    "monitoring"
]

# Cache for creating duplicates
event_cache = []
CACHE_SIZE = 50


def generate_event():
    """Generate a random event"""
    return {
        "topic": random.choice(TOPICS),
        "event_id": f"evt-{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "source": random.choice(SOURCES),
        "payload": {
            "session_id": f"session-{random.randint(1000, 9999)}",
            "user_id": f"user-{random.randint(1, 100)}",
            "action": random.choice(["create", "read", "update", "delete"]),
            "status": random.choice(["success", "failure", "pending"]),
            "duration_ms": random.randint(10, 1000),
            "data": f"sample-data-{random.randint(1, 1000)}"
        }
    }


def should_send_duplicate():
    """Determine if we should send a duplicate based on rate"""
    return random.random() < DUPLICATE_RATE


def publish_events():
    """Publish events to aggregator"""
    try:
        # Determine if this batch should include duplicates
        if event_cache and should_send_duplicate():
            # Send a duplicate from cache
            event = random.choice(event_cache)
            logger.info(f"Publishing DUPLICATE event: {event['event_id']}")
        else:
            # Send new event
            event = generate_event()
            logger.info(f"Publishing NEW event: {event['event_id']}")
            
            # Add to cache for future duplicates
            event_cache.append(event)
            if len(event_cache) > CACHE_SIZE:
                event_cache.pop(0)
        
        # Send to aggregator
        response = requests.post(
            f"{AGGREGATOR_URL}/publish",
            json=event,
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"Event published successfully: {response.json()}")
        else:
            logger.error(f"Failed to publish event: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error publishing event: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def main():
    """Main publisher loop"""
    logger.info("=" * 60)
    logger.info("UTS Publisher Simulator Started")
    logger.info(f"Aggregator URL: {AGGREGATOR_URL}")
    logger.info(f"Publish Interval: {PUBLISH_INTERVAL}s")
    logger.info(f"Duplicate Rate: {DUPLICATE_RATE * 100}%")
    logger.info("=" * 60)
    
    # Wait for aggregator to be ready
    logger.info("Waiting for aggregator to be ready...")
    for i in range(30):
        try:
            response = requests.get(f"{AGGREGATOR_URL}/health", timeout=2)
            if response.status_code == 200:
                logger.info("Aggregator is ready!")
                break
        except:
            pass
        time.sleep(2)
    else:
        logger.warning("Aggregator not ready after 60s, proceeding anyway...")
    
    # Main publishing loop
    event_count = 0
    try:
        while True:
            event_count += 1
            logger.info(f"\n--- Event #{event_count} ---")
            publish_events()
            time.sleep(PUBLISH_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("\nPublisher stopped by user")
    except Exception as e:
        logger.error(f"Publisher error: {e}")


if __name__ == "__main__":
    main()
