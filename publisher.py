import asyncio
import aiohttp
import uuid
import random
from datetime import datetime, timezone

API_URL = "http://aggregator:8080/publish"
TOPICS = ["user-activity", "system-log", "transaction", "security-event", "performance-metric"]
SOURCES = ["raspberry-pi", "iot-hub", "mobile-app"]

TOTAL_EVENTS = 5000
DUPLICATION_RATE = 0.2
CONCURRENCY_LIMIT = 100 

def generate_event(topic=None, source=None):
    return {
        "topic": topic or random.choice(TOPICS),
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source or random.choice(SOURCES),
        "payload": {
            "value": random.randint(0, 100),
            "status": random.choice(["ok", "warn", "error"])
        }
    }

async def send_event(session, event, sem, idx=None):
    async with sem:
        try:
            async with session.post(API_URL, json=event) as resp:
                status = resp.status
                if idx is not None:
                    print(f"[SEND] #{idx+1} event_id={event['event_id']} topic={event['topic']} status={status}")
                if status == 200:
                    return "ok"
                elif status == 409:
                    return "duplicate"
                else:
                    return f"error-{status}"
        except Exception as e:
            print(f"[ERROR] event_id={event['event_id']} error={e}")
            return f"fail-{e}"

async def wait_for_aggregator(url, timeout=60):
    for _ in range(timeout):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        print("Aggregator is ready!")
                        return
        except Exception:
            pass
        print("Waiting for aggregator to be ready...")
        await asyncio.sleep(1)
    print("Aggregator not ready after waiting, proceeding anyway...")

async def main():
    await wait_for_aggregator("http://aggregator:8080/health")

    sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

    events = [generate_event() for _ in range(TOTAL_EVENTS)]
    duplicates = random.sample(events, int(TOTAL_EVENTS * DUPLICATION_RATE))
    all_events = events + duplicates
    random.shuffle(all_events)

    print(f"Sending {len(all_events)} events ({TOTAL_EVENTS} unique + {len(duplicates)} duplicates)...")

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *(send_event(session, event, sem, idx) for idx, event in enumerate(all_events))
        )

if __name__ == "__main__":
    asyncio.run(main())