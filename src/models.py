"""
Data models for events and API responses.
Implements event schema validation with Pydantic.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class Event(BaseModel):
    """
    Event model representing a log/event in the system.
    
    Attributes:
        topic: Topic/category of the event
        event_id: Unique identifier for the event (collision-resistant)
        timestamp: ISO8601 formatted timestamp
        source: Source system/service that generated the event
        payload: Arbitrary JSON payload containing event data
    """
    topic: str = Field(..., min_length=1, max_length=255)
    event_id: str = Field(..., min_length=1, max_length=255)
    timestamp: str = Field(..., description="ISO8601 formatted timestamp")
    source: str = Field(..., min_length=1, max_length=255)
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamp is in valid ISO8601 format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid ISO8601 timestamp: {v}")
    
    def get_dedup_key(self) -> str:
        """Generate deduplication key from topic and event_id"""
        return f"{self.topic}:{self.event_id}"


class ProcessedEvent(Event):
    """Event with processing metadata"""
    processed_at: str = Field(..., description="When the event was processed")


class PublishResponse(BaseModel):
    """Response for publish endpoint"""
    status: str
    received: int
    message: str


class EventsResponse(BaseModel):
    """Response for events query endpoint"""
    events: List[ProcessedEvent]
    total: int
    filtered_by_topic: Optional[str] = None


class StatsResponse(BaseModel):
    """Response for statistics endpoint"""
    received: int = Field(..., description="Total events received")
    unique_processed: int = Field(..., description="Unique events processed")
    duplicate_dropped: int = Field(..., description="Duplicate events dropped")
    topics: List[str] = Field(..., description="List of unique topics")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    started_at: str = Field(..., description="Service start timestamp")


class HealthResponse(BaseModel):
    """Response for health check endpoint"""
    status: str
    timestamp: str
