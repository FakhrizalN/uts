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

## 📋 Checklist UTS

### ✅ Requirement Wajib

- [x] **Bahasa**: Python 3.11
- [x] **Framework**: FastAPI + asyncio
- [x] **Idempotent Consumer**: Implemented dengan dedup store
- [x] **Deduplication**: SQLite dengan UNIQUE constraint
- [x] **At-least-once Delivery**: Retry-safe dengan idempotency
- [x] **Persistent Storage**: SQLite WAL mode
- [x] **Docker**: Dockerfile dengan non-root user
- [x] **Unit Tests**: 42 tests (exceeds 5-10 requirement)
- [x] **API Endpoints**: /publish, /events, /stats, /health
- [x] **Scale Test**: 5000+ events dengan 20% duplikasi
- [x] **Laporan**: report.md dengan analisis Bab 1-7

### 🎁 BONUS

- [x] **Docker Compose**: Multi-service orchestration
- [x] **Publisher Simulator**: Automated testing
- [x] **Comprehensive Tests**: 42 tests dengan coverage
- [x] **Performance Benchmarks**: Throughput, latency tests
- [x] **Documentation**: README, CONTRIBUTING, comments

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Manual testing
python test_manual.py
```

### Expected Results
```
✓ 42 tests passed
✓ Throughput: ~1190 events/s
✓ Duplicate detection: 100%
✓ All API endpoints working
```

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

## 📁 File Penting

| File | Deskripsi |
|------|-----------|
| `README.md` | Dokumentasi lengkap sistem |
| `report.md` | Laporan teori (Bab 1-7) dan implementasi |
| `src/main.py` | Entry point aplikasi |
| `Dockerfile` | Docker image definition |
| `docker-compose.yml` | Multi-service orchestration |
| `requirements.txt` | Python dependencies |
| `tests/` | Unit tests (42 tests) |

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

## 📦 Deliverables Checklist

Untuk submit, pastikan repository berisi:

- [x] `README.md` - Dokumentasi cara run
- [x] `report.md` - Laporan lengkap dengan teori
- [x] `src/` - Source code
- [x] `tests/` - Unit tests
- [x] `Dockerfile` - Docker image
- [x] `docker-compose.yml` - Multi-service (BONUS)
- [x] `requirements.txt` - Dependencies
- [x] `.gitignore` - Exclude unnecessary files
- [ ] Video demo (upload ke YouTube, tambahkan link di README)

## 🔗 Next Steps

1. **Sebelum Submit**:
   - Run all tests: `pytest tests/ -v`
   - Build Docker: `docker build -t uts-aggregator .`
   - Test Docker run: `docker run -p 8080:8080 uts-aggregator`
   - Update nama/NIM di report.md
   - Record video demo
   - Upload video ke YouTube (public)
   - Add video link to README.md

2. **Submit**:
   - Push ke GitHub
   - Submit link GitHub + link video
   - Submit report.pdf (atau report.md)

## ❓ Troubleshooting

### Issue: "Module not found"
```bash
# Pastikan di root directory
cd d:\Tugas Sem 7\Sister\uts

# Run dengan module syntax
python -m src.main
```

### Issue: "Port 8080 already in use"
```bash
# Windows: cari process
netstat -ano | findstr :8080

# Kill process atau ganti port di config.py
```

### Issue: Docker build gagal
```bash
# Clean cache
docker system prune -a

# Rebuild
docker build --no-cache -t uts-aggregator .
```

## 📧 Support

Jika ada pertanyaan:
1. Check dokumentasi (README, report, code comments)
2. Review test files untuk contoh usage
3. Run `python test_manual.py` untuk test interaktif

---

**Good luck! 🎓**

Proyek ini sudah memenuhi semua requirement UTS + BONUS. Tinggal:
1. Update nama/NIM
2. Test semua fitur
3. Record video demo
4. Submit!
