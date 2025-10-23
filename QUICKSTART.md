# Quick Start Guide - UTS Log Aggregator

## 🚀 Panduan Cepat

### Cara Tercepat (Docker)

```bash
# 1. Build image
docker build -t uts-aggregator .

# 2. Run container
docker run -p 8080:8080 uts-aggregator

# 3. Akses API
# Browser: http://localhost:8080/docs
```

### Dengan Docker Compose (BONUS)

```bash
# Start semua services (aggregator + publisher simulator)
docker-compose up --build

# Stop
docker-compose down
```

### Development Lokal (Tanpa Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run application
python -m src.main

# 3. Akses di http://localhost:8080
```

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Manual testing
python test_manual.py

## 📊 Demo Scenarios

### Scenario 1: Publish & Query
```bash
# Publish event
curl -X POST http://localhost:8080/publish \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","event_id":"evt-001","timestamp":"2025-10-21T10:00:00Z","source":"demo","payload":{}}'

# Query events
curl http://localhost:8080/events?topic=test

# Check stats
curl http://localhost:8080/stats
```

### Scenario 2: Duplicate Detection
```bash
# Send same event 3 times
for i in {1..3}; do
  curl -X POST http://localhost:8080/publish \
    -H "Content-Type: application/json" \
    -d '{"topic":"test","event_id":"evt-dup","timestamp":"2025-10-21T10:00:00Z","source":"demo","payload":{}}'
done

# Check stats - should show: received=3, unique_processed=1, duplicate_dropped=2
curl http://localhost:8080/stats
```

### Scenario 3: Persistence After Restart
```bash
# 1. Publish event
curl -X POST http://localhost:8080/publish -H "Content-Type: application/json" \
  -d '{"topic":"persist","event_id":"evt-persist","timestamp":"2025-10-21T10:00:00Z","source":"demo","payload":{}}'

# 2. Stop container
docker stop <container_id>

# 3. Start container
docker start <container_id>

# 4. Send same event again
curl -X POST http://localhost:8080/publish -H "Content-Type: application/json" \
  -d '{"topic":"persist","event_id":"evt-persist","timestamp":"2025-10-21T10:00:00Z","source":"demo","payload":{}}'

# 5. Should be detected as duplicate
curl http://localhost:8080/stats
```

## 🎥 Video Demo

Untuk membuat video demo (5-8 menit), cover:

1. **Build & Run** (1 min)
   - `docker build` command
   - `docker run` command
   - Show service running

2. **API Demo** (2 min)
   - Publish single event
   - Publish batch events
   - Query events
   - Check statistics

3. **Duplicate Detection** (2 min)
   - Send duplicate events
   - Show logs detecting duplicates
   - Verify stats (duplicate_dropped count)

4. **Persistence Test** (2 min)
   - Publish events
   - Restart container
   - Send duplicates
   - Show dedup still works

5. **Architecture Overview** (1 min)
   - Explain components
   - Show diagram
   - Mention key design decisions

