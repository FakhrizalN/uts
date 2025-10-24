# UTS Sistem Terdistribusi - Pub-Sub Log Aggregator

## Deskripsi Sistem
Layanan Pub-Sub log aggregator dengan idempotent consumer dan deduplication yang berjalan dalam Docker container. Sistem ini menerima event/log dari publisher dan memproses melalui subscriber yang bersifat idempotent, mencegah pemrosesan ulang event yang sama.

## Fitur Utama
- Idempotent consumer untuk mencegah duplikasi pemrosesan
- Deduplication store persisten (SQLite)
- At-least-once delivery semantics
- Toleransi kegagalan dengan persistensi data
- API RESTful untuk publish dan query events
- Statistik dan monitoring real-time
- Unit tests komprehensif (>5 tests)
- Docker container support
- Docker Compose untuk multi-service orchestration (BONUS)

## Arsitektur Sistem

```
┌──────────────┐         ┌────────────────────────┐
│  Publisher   │────────>│  POST /publish         │
│  (Client)    │         │                        │
└──────────────┘         │   Aggregator Service   │
                         │                        │
                         │  ┌──────────────────┐  │
                         │  │ Event Queue      │  │
                         │  │ (asyncio.Queue)  │  │
                         │  └────────┬─────────┘  │
                         │           │            │
                         │           ▼            │
                         │  ┌──────────────────┐  │
                         │  │ Dedup Consumer   │  │
                         │  │ (Idempotent)     │  │
                         │  └────────┬─────────┘  │
                         │           │            │
                         │           ▼            │
                         │  ┌──────────────────┐  │
                         │  │ SQLite Dedup DB  │  │
                         │  │ (Persistent)     │  │
                         │  └──────────────────┘  │
                         │                        │
                         │  GET /events           │
                         │  GET /stats            │
                         └────────────────────────┘
```

## Teknologi Stack
- **Language**: Python 3.11
- **Framework**: FastAPI + asyncio
- **Database**: SQLite (dedup store)
- **Containerization**: Docker
- **Orchestration**: Docker Compose (bonus)
- **Testing**: pytest

## Struktur Direktori

```
uts/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point aplikasi
│   ├── models.py            # Model Event dan Response
│   ├── dedup_store.py       # SQLite-based deduplication store
│   ├── consumer.py          # Idempotent consumer logic
│   ├── api.py               # FastAPI endpoints
│   └── config.py            # Konfigurasi aplikasi
├── tests/
│   ├── __init__.py
│   ├── test_dedup.py        # Test deduplication
│   ├── test_api.py          # Test API endpoints
│   ├── test_persistence.py  # Test persistensi
│   ├── test_idempotency.py  # Test idempotency
│   └── test_performance.py  # Test performa
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Multi-service orchestration (BONUS)
├── .dockerignore
├── README.md               # Dokumentasi ini
└── report.md               # Laporan lengkap dengan analisis teori
```

## Instalasi & Menjalankan Aplikasi

### Prasyarat
- Docker Desktop terinstall
- Python 3.11+ (untuk development lokal)

### Cara 1: Menggunakan Docker (Production)

#### Build Image
```bash
docker build -t uts-aggregator .
```

#### Run Container
```bash
docker run -p 8080:8080 -v %cd%/data:/app/data uts-aggregator
```

**Catatan**: Volume mount `-v %cd%/data:/app/data` memastikan persistensi data setelah restart container.

### Cara 2: Menggunakan Docker Compose

#### Build & Run Semua Services
```bash
docker-compose up --build
```

#### Stop Services
```bash
docker-compose down
```

### Cara 3: Development Lokal (Tanpa Docker)

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Run Application
```bash
python -m src.main
```

## API Endpoints

### 1. Publish Event
**POST** `/publish`

Menerima single event atau batch events.

**Request Body (Single Event)**:
```json
{
  "topic": "user-activity",
  "event_id": "evt-12345-abcde",
  "timestamp": "2025-10-21T10:30:00Z",
  "source": "web-app",
  "payload": {
    "user_id": "user-001",
    "action": "login"
  }
}
```

**Request Body (Batch Events)**:
```json
[
  {
    "topic": "user-activity",
    "event_id": "evt-12345-abcde",
    "timestamp": "2025-10-21T10:30:00Z",
    "source": "web-app",
    "payload": {"user_id": "user-001", "action": "login"}
  },
  {
    "topic": "system-log",
    "event_id": "evt-67890-fghij",
    "timestamp": "2025-10-21T10:31:00Z",
    "source": "backend",
    "payload": {"level": "INFO", "message": "Service started"}
  }
]
```

**Response**:
```json
{
  "status": "success",
  "received": 2,
  "message": "Events queued for processing"
}
```

### 2. Get Events
**GET** `/events?topic={topic}&limit={limit}`

Query parameters:
- `topic` (optional): Filter by topic
- `limit` (optional, default=100): Limit hasil

**Response**:
```json
{
  "events": [
    {
      "topic": "user-activity",
      "event_id": "evt-12345-abcde",
      "timestamp": "2025-10-21T10:30:00Z",
      "source": "web-app",
      "payload": {"user_id": "user-001", "action": "login"},
      "processed_at": "2025-10-21T10:30:01Z"
    }
  ],
  "total": 1,
  "filtered_by_topic": "user-activity"
}
```

### 3. Get Statistics
**GET** `/stats`

**Response**:
```json
{
  "received": 5000,
  "unique_processed": 4000,
  "duplicate_dropped": 1000,
  "topics": ["user-activity", "system-log", "transaction"],
  "uptime_seconds": 3600.5,
  "started_at": "2025-10-21T09:00:00Z"
}
```

### 4. Health Check
**GET** `/health`

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T10:30:00Z"
}
```

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_dedup.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```


## Video Demo

🎥 **Link YouTube**: https://youtu.be/rssHJGNFtGE