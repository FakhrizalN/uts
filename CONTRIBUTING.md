# Contributing Guide

## Development Setup

### Prerequisites
- Python 3.11+
- Docker Desktop (untuk containerization)
- Git

### Local Development

1. **Clone Repository**
```bash
git clone <your-repo-url>
cd uts
```

2. **Create Virtual Environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Run Application**
```bash
python -m src.main
```

5. **Access API**
- Swagger UI: http://localhost:8080/docs
- API Base: http://localhost:8080

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/test_dedup.py -v
```

### Run Manual Test Script
```bash
# Start service first
python -m src.main

# In another terminal
python test_manual.py
```

## Docker

### Build Image
```bash
docker build -t uts-aggregator .
```

### Run Container
```bash
docker run -p 8080:8080 -v %cd%/data:/app/data uts-aggregator
```

### Docker Compose (Multi-service)
```bash
docker-compose up --build
```

## Code Structure

```
src/
├── config.py         # Configuration management
├── models.py         # Pydantic data models
├── dedup_store.py    # SQLite persistence layer
├── consumer.py       # Idempotent consumer logic
├── api.py            # FastAPI endpoints
└── main.py           # Application entry point

tests/
├── test_dedup.py        # Deduplication tests
├── test_idempotency.py  # Idempotency tests
├── test_persistence.py  # Restart persistence tests
├── test_api.py          # API endpoint tests
└── test_performance.py  # Performance benchmarks
```

## Coding Standards

### Style Guide
- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep functions small and focused

### Example
```python
def store_event(self, event: Event) -> bool:
    """
    Store an event in the dedup store (idempotent operation).
    
    Args:
        event: Event to store
        
    Returns:
        True if event was newly stored, False if it was a duplicate
    """
    # Implementation
```

### Commit Messages
- Use imperative mood ("Add feature" not "Added feature")
- Keep first line under 50 characters
- Provide detailed description if needed

Example:
```
Add deduplication support for multi-topic events

- Implement composite key (topic, event_id)
- Add database indexes for performance
- Update tests to cover multi-topic scenarios
```

## Performance Guidelines

### Target Metrics
- Throughput: >= 1000 events/second
- Latency: < 100ms p99
- Memory: < 256MB under load
- Duplicate detection: 100% accuracy

### Benchmarking
```bash
pytest tests/test_performance.py -v
```

## Troubleshooting

### Common Issues

**1. Import errors**
```bash
# Ensure you're in the project root
cd d:\Tugas Sem 7\Sister\uts

# Run with module syntax
python -m src.main
```

**2. Database locked**
```bash
# Remove existing database
rm data/dedup_store.db*

# Restart application
```

**3. Port already in use**
```bash
# Check what's using port 8080
netstat -ano | findstr :8080

# Kill the process or change PORT in config.py
```

**4. Docker build fails**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild
docker build --no-cache -t uts-aggregator .
```

## Adding New Features

### Step-by-Step

1. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Implement Feature**
- Write code following standards
- Add type hints
- Document functions

3. **Add Tests**
- Write unit tests in appropriate test file
- Ensure >= 80% coverage for new code

4. **Run Tests**
```bash
pytest tests/ -v
```

5. **Update Documentation**
- Update README.md if needed
- Update report.md for theoretical aspects

6. **Commit and Push**
```bash
git add .
git commit -m "Add feature: description"
git push origin feature/your-feature-name
```

## Questions?

For questions or issues, please:
1. Check existing documentation (README.md, report.md)
2. Review code comments
3. Run tests to understand expected behavior
4. Create an issue in repository

---

Happy coding! 🚀
