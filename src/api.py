"""
FastAPI application with REST endpoints.
Provides API for publishing events and querying aggregated logs.
"""
import logging
from datetime import datetime
from typing import List, Union, Optional, Dict

from fastapi import FastAPI, Request, HTTPException, Query, Body
from fastapi.responses import JSONResponse

from .models import (
    Event, PublishResponse, EventsResponse, 
    StatsResponse, HealthResponse
)
from .consumer import Consumer
from .dedup_store import DedupStore

logger = logging.getLogger(__name__)


def create_app(consumer: Consumer, dedup_store: DedupStore, start_time: datetime) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        consumer: Consumer instance for statistics
        dedup_store: Dedup store for querying events
        start_time: Application start timestamp
        
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="UTS Log Aggregator",
        description="Pub-Sub Log Aggregator with Idempotent Consumer and Deduplication",
        version="1.0.0"
    )
    
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint"""
        return {
            "service": "UTS Log Aggregator",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "publish": "POST /publish",
                "events": "GET /events",
                "stats": "GET /stats",
                "health": "GET /health"
            }
        }
    
    @app.post("/publish", tags=["Events"])
    async def publish_event(request: Request, events: Union[Dict, List[Dict]] = Body(...)):
        """
        Publish single event or batch of events to the aggregator.
        
        Events are queued for asynchronous processing by the idempotent consumer.
        Duplicate events (same topic + event_id) will be automatically deduplicated.
        
        Args:
            request: FastAPI request object
            events: Single Event or list of Events in dictionary form
            
        Returns:
            JSON response with status and count of queued events
        """
        try:
            consumer = getattr(request.app.state, "consumer", None)
            dedup_store = getattr(request.app.state, "dedup_store", None)
            if consumer is None or dedup_store is None:
                raise HTTPException(status_code=503, detail="Service not ready")

            batch = events if isinstance(events, list) else [events]
            event_objs = []
            duplicate_count = 0
            for ev in batch:
                event_obj = Event(**ev)
                # Cek duplikat sebelum masuk queue
                if dedup_store.is_duplicate(event_obj):
                    duplicate_count += 1
                    continue
                await consumer.queue.put(event_obj)
                event_objs.append(event_obj)

            if duplicate_count == len(batch):
                # Semua event duplikat
                return JSONResponse(status_code=409, content={"detail": "Duplicate event(s) detected"})
            elif duplicate_count > 0:
                return {"status": "queued", "queued_count": len(event_objs), "duplicate_count": duplicate_count}
            else:
                return {"status": "queued", "queued_count": len(event_objs)}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error in publish endpoint: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to queue events: {e}")
    
    @app.get("/events", response_model=EventsResponse, tags=["Events"])
    async def get_events(
        request: Request, 
        topic: Optional[str] = Query(None, description="Filter by topic"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum events to return")
    ):
        """
        Retrieve processed events from the aggregator.
        
        Query parameters:
            - topic: Optional filter by topic name
            - limit: Maximum number of events to return (1-1000, default 100)
            
        Returns:
            EventsResponse with list of processed events
        """
        try:
            dedup_store = getattr(request.app.state, "dedup_store", None)
            if dedup_store is None:
                raise HTTPException(status_code=503, detail="Service not ready: dedup_store not initialized")
            
            events = await asyncio.to_thread(
                dedup_store.get_events,
                topic=topic,
                limit=limit
            )
            
            return EventsResponse(
                events=events,
                total=len(events),
                filtered_by_topic=topic
            )
            
        except Exception as e:
            logger.error("Error in get_events endpoint: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to retrieve events: {e}")
    
    @app.get("/stats")
    async def get_stats(request: Request):
        """
        Get aggregator statistics and metrics.
        
        Returns:
            JSON response with:
            - received: Total events received
            - unique_processed: Unique events processed
            - duplicate_dropped: Duplicate events dropped
            - topics: List of unique topics
            - uptime_seconds: Service uptime
            - started_at: Service start timestamp
        """
        try:
            dedup_store = getattr(request.app.state, "dedup_store", None)
            if dedup_store is None:
                raise HTTPException(status_code=503, detail="Service not ready: dedup_store not initialized")
            
            stats = dedup_store.get_stats()
            stats["uptime"] = str(datetime.utcnow() - request.app.state.start_time)
            
            return stats
            
        except Exception as e:
            logger.error("Error in get_stats endpoint: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {e}")
    
    @app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
    async def health_check():
        """
        Health check endpoint.
        
        Returns:
            HealthResponse with status and current timestamp
        """
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    
    import asyncio
    
    return app
