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
            if consumer is None:
                # service belum siap
                raise HTTPException(status_code=503, detail="Service not ready: consumer not initialized")

            batch = events if isinstance(events, list) else [events]
            event_objs = []
            for ev in batch:
                event_obj = Event(**ev)  # <-- PARSE DI SINI
                await consumer.queue.put(event_obj)
                event_objs.append(event_obj)

            logger.info(f"Queued {len(event_objs)} events for processing")
            
            return {"status": "queued", "queued_count": len(event_objs)}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error in publish endpoint: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to queue events: {e}")
    
    @app.get("/events", response_model=EventsResponse, tags=["Events"])
    async def get_events(
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
            logger.error(f"Error in get_events endpoint: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve events: {str(e)}"
            )
    
    @app.get("/stats", response_model=StatsResponse, tags=["Monitoring"])
    async def get_stats():
        """
        Get aggregator statistics and metrics.
        
        Returns:
            StatsResponse with:
            - received: Total events received
            - unique_processed: Unique events processed
            - duplicate_dropped: Duplicate events dropped
            - topics: List of unique topics
            - uptime_seconds: Service uptime
            - started_at: Service start timestamp
        """
        try:
            # Get consumer stats
            consumer_stats = consumer.get_stats()
            
            # Get dedup store stats
            unique_processed, topics = await asyncio.to_thread(
                dedup_store.get_stats
            )
            
            # Calculate uptime
            uptime = (datetime.utcnow() - start_time).total_seconds()
            
            return StatsResponse(
                received=consumer_stats['received'],
                unique_processed=unique_processed,
                duplicate_dropped=consumer_stats['duplicate_dropped'],
                topics=topics,
                uptime_seconds=uptime,
                started_at=start_time.isoformat() + 'Z'
            )
            
        except Exception as e:
            logger.error(f"Error in stats endpoint: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve stats: {str(e)}"
            )
    
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
    
    # Add asyncio import for to_thread
    import asyncio
    
    return app
