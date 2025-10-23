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
        
        # Statistics counters
        self.received_count = 0
        self.unique_count = 0
        self.duplicate_count = 0
        self.topics = set()
        
        # Batch processing optimization
        self._batch_events = []
        self._batch_size = 50  # Commit every 50 events
        
        # Keep a persistent connection for better performance
        self._conn = None
        
        self._init_db()
        logger.info(f"DedupStore initialized at {db_path}")
    
    def _init_db(self):
        """Initialize database schema with proper indexes"""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # NORMAL is faster than FULL, still safe with WAL
            conn.execute("PRAGMA synchronous=NORMAL")
            # Increase cache size for better performance (10MB)
            conn.execute("PRAGMA cache_size=-10000")
            # Store temp tables in memory
            conn.execute("PRAGMA temp_store=MEMORY")
            # Optimize for write-heavy workload
            conn.execute("PRAGMA locking_mode=EXCLUSIVE")
            
            
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
        """Context manager for database connections with connection reuse"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Additional performance optimizations
            self._conn.execute("PRAGMA cache_size=-10000")
            self._conn.execute("PRAGMA temp_store=MEMORY")
        
        try:
            yield self._conn
        except Exception:
            if self._conn:
                self._conn.rollback()
            raise
    
    def is_duplicate(self, event: Event) -> bool:
        """
        Check if an event has already been processed.
        Updates duplicate count if event is a duplicate.
        """
        with self._get_connection() as conn:
            # Use EXISTS for better performance (stops at first match)
            cursor = conn.execute(
                """SELECT EXISTS(
                    SELECT 1 FROM processed_events 
                    WHERE topic = ? AND event_id = ? 
                    LIMIT 1
                ) as is_dup""",
                (event.topic, event.event_id)
            )
            result = cursor.fetchone()
            if result['is_dup']:
                self.duplicate_count += 1
                return True
            return False
    
    def store_event(self, event: Event) -> bool:
        """
        Store an event in the dedup store (idempotent operation).
        
        Args:
            event: Event to store
            
        Returns:
            True if event was newly stored, False if it was a duplicate
        """
        processed_at = datetime.utcnow().isoformat() + 'Z'
        self.received_count += 1
        self.topics.add(event.topic)
        try:
            with self._get_connection() as conn:
                import json
                # Use INSERT OR IGNORE for better performance
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO processed_events 
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
                # Check if row was actually inserted
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.debug(f"Stored new event: {event.get_dedup_key()}")
                    self.unique_count += 1
                    return True
                else:
                    # Was duplicate
                    logger.info(f"Duplicate event dropped: {event.get_dedup_key()}")
                    self.duplicate_count += 1
                    return False
        except sqlite3.IntegrityError:
            logger.info(f"Duplicate event dropped: {event.get_dedup_key()}")
            self.duplicate_count += 1
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
    
    def get_stats(self):
        """
        Get statistics from the dedup store.
        """
        with self._get_connection() as conn:
            
            cursor = conn.execute("SELECT COUNT(*) as count FROM processed_events")
            unique_count = cursor.fetchone()['count']

            
            cursor = conn.execute("SELECT DISTINCT topic FROM processed_events ORDER BY topic")
            topics = [row['topic'] for row in cursor.fetchall()]

            
            return {
                "received": self.received_count,
                "unique_processed": unique_count,
                "duplicate_dropped": self.duplicate_count,  
                "topics": topics,
            }
    
    def clear_all(self):
        """Clear all events from the store (for testing purposes)"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM processed_events")
            conn.commit()
            logger.warning("All events cleared from dedup store")
    
    def close(self):
        """Close the database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")
