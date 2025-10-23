
FROM python:3.11-slim AS builder


WORKDIR /app


RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim


WORKDIR /app


RUN adduser --disabled-password --gecos '' appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app


COPY --from=builder /root/.local /home/appuser/.local


COPY --chown=appuser:appuser src/ ./src/


USER appuser


ENV PATH=/home/appuser/.local/bin:$PATH


ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV PORT=8080


EXPOSE 8080


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1


CMD ["python", "-m", "src.main"]
