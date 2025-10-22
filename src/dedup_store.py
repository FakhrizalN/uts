"""
Deduplication store implementation using SQLite.
Provides persistent, atomic storage for tracking processed events.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
from contextlib import contextmanager

from .models import Event, ProcessedEvent

logger = logging.getLogger(__name__)


class DedupStore:
    """
    SQLite-based deduplication store for idempotent event processing.
    
    Uses Write-Ahead Logging (WAL) mode for better concurrency and crash recovery.
    Stores processed events with their metadata to prevent reprocessing.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize the dedup store.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_db()
        logger.info(f"DedupStore initialized at {db_path}")
    
    def _init_db(self):
        """Initialize database schema with proper indexes"""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency and durability
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            # Create events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    UNIQUE(topic, event_id)
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_topic 
                ON processed_events(topic)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_id 
                ON processed_events(event_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_events(processed_at)
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def is_duplicate(self, event: Event) -> bool:
        """
        Check if an event has already been processed.
        
        Args:
            event: Event to check
            
        Returns:
            True if event is a duplicate, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM processed_events WHERE topic = ? AND event_id = ?",
                (event.topic, event.event_id)
            )
            result = cursor.fetchone()
            return result['count'] > 0
    
    def store_event(self, event: Event) -> bool:
        """
        Store an event in the dedup store (idempotent operation).
        
        Args:
            event: Event to store
            
        Returns:
            True if event was newly stored, False if it was a duplicate
        """
        processed_at = datetime.utcnow().isoformat() + 'Z'
        
        try:
            with self._get_connection() as conn:
                import json
                conn.execute(
                    """
                    INSERT INTO processed_events 
                    (topic, event_id, timestamp, source, payload, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.topic,
                        event.event_id,
                        event.timestamp,
                        event.source,
                        json.dumps(event.payload),
                        processed_at
                    )
                )
                conn.commit()
                logger.debug(f"Stored new event: {event.get_dedup_key()}")
                return True
        except sqlite3.IntegrityError:
            # Duplicate event (UNIQUE constraint violation)
            logger.info(f"Duplicate event dropped: {event.get_dedup_key()}")
            return False
    
    def get_events(self, topic: Optional[str] = None, limit: int = 100) -> List[ProcessedEvent]:
        """
        Retrieve processed events from the store.
        
        Args:
            topic: Optional topic filter
            limit: Maximum number of events to return
            
        Returns:
            List of ProcessedEvent objects
        """
        with self._get_connection() as conn:
            if topic:
                cursor = conn.execute(
                    """
                    SELECT topic, event_id, timestamp, source, payload, processed_at
                    FROM processed_events
                    WHERE topic = ?
                    ORDER BY processed_at DESC
                    LIMIT ?
                    """,
                    (topic, limit)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT topic, event_id, timestamp, source, payload, processed_at
                    FROM processed_events
                    ORDER BY processed_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            
            events = []
            import json
            for row in cursor.fetchall():
                events.append(ProcessedEvent(
                    topic=row['topic'],
                    event_id=row['event_id'],
                    timestamp=row['timestamp'],
                    source=row['source'],
                    payload=json.loads(row['payload']),
                    processed_at=row['processed_at']
                ))
            
            return events
    
    def get_stats(self) -> Tuple[int, List[str]]:
        """
        Get statistics from the dedup store.
        
        Returns:
            Tuple of (unique_processed_count, list_of_topics)
        """
        with self._get_connection() as conn:
            # Get unique processed count
            cursor = conn.execute("SELECT COUNT(*) as count FROM processed_events")
            unique_count = cursor.fetchone()['count']
            
            # Get unique topics
            cursor = conn.execute("SELECT DISTINCT topic FROM processed_events ORDER BY topic")
            topics = [row['topic'] for row in cursor.fetchall()]
            
            return unique_count, topics
    
    def clear_all(self):
        """Clear all events from the store (for testing purposes)"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM processed_events")
            conn.commit()
            logger.warning("All events cleared from dedup store")
