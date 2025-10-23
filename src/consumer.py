"""
Idempotent consumer implementation.
Processes events from queue with deduplication logic.
"""
import asyncio
import logging
from typing import Optional

from .models import Event
from .dedup_store import DedupStore

logger = logging.getLogger(__name__)


class Consumer:
    """
    Idempotent consumer that processes events from a queue.
    
    Ensures each unique event (by topic + event_id) is processed exactly once,
    even if received multiple times (at-least-once delivery semantics).
    """
    
    def __init__(
        self,
        queue: asyncio.Queue,
        dedup_store: DedupStore,
        batch_size: int = 100,
        sleep_interval: float = 0.01
    ):
        """
        Initialize the consumer.
        
        Args:
            queue: Asyncio queue to consume events from
            dedup_store: Deduplication store for tracking processed events
            batch_size: Number of events to process in one batch
            sleep_interval: Sleep time when queue is empty (seconds)
        """
        self.queue = queue
        self.dedup_store = dedup_store
        self.batch_size = batch_size
        self.sleep_interval = sleep_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        
        self.stats = {
            'received': 0,
            'unique_processed': 0,
            'duplicate_dropped': 0
        }
    
    async def start(self):
        """Start the consumer task"""
        if self.running:
            logger.warning("Consumer already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("Consumer started")
    
    async def stop(self):
        """Stop the consumer and wait for graceful shutdown"""
        if not self.running:
            return
        
        self.running = False
        if self._task:
            
            await self._task
        logger.info("Consumer stopped")
    
    async def _consume_loop(self):
        """Main consumer loop that processes events from queue"""
        logger.info("Consumer loop started")
        
        while self.running or not self.queue.empty():
            try:
                
                batch = []
                
                
                for _ in range(self.batch_size):
                    try:
                        event = self.queue.get_nowait()
                        batch.append(event)
                    except asyncio.QueueEmpty:
                        break
                
                if batch:
                    await self._process_batch(batch)
                else:
                    
                    await asyncio.sleep(self.sleep_interval)
                    
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                await asyncio.sleep(self.sleep_interval)
        
        logger.info("Consumer loop finished")
    
    async def _process_batch(self, events: list[Event]):
        """
        Process a batch of events with deduplication.
        
        Args:
            events: List of events to process
        """
        # Process events synchronously in batch for better performance
        for event in events:
            try:
                self.stats['received'] += 1
                
                # Direct synchronous call for better performance in tight loop
                is_new = self.dedup_store.store_event(event)
                
                if is_new:
                    self.stats['unique_processed'] += 1
                    logger.debug(
                        f"Processed new event: {event.get_dedup_key()} "
                        f"from topic '{event.topic}'"
                    )
                else:
                    self.stats['duplicate_dropped'] += 1
                    logger.info(
                        f"Dropped duplicate event: {event.get_dedup_key()} "
                        f"from topic '{event.topic}'"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error processing event {event.get_dedup_key()}: {e}",
                    exc_info=True
                )
    
    async def _process_event(self, event: Event):
        """
        Process a single event (idempotent operation).
        
        Args:
            event: Event to process
        """
        try:
            self.stats['received'] += 1
            
            # Direct synchronous call
            is_new = self.dedup_store.store_event(event)
            
            if is_new:
                self.stats['unique_processed'] += 1
                logger.debug(
                    f"Processed new event: {event.get_dedup_key()} "
                    f"from topic '{event.topic}'"
                )
            else:
                self.stats['duplicate_dropped'] += 1
                logger.info(
                    f"Dropped duplicate event: {event.get_dedup_key()} "
                    f"from topic '{event.topic}'"
                )
                
        except Exception as e:
            logger.error(
                f"Error processing event {event.get_dedup_key()}: {e}",
                exc_info=True
            )
    
    def get_stats(self) -> dict:
        """Get consumer statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset consumer statistics"""
        self.stats = {
            'received': 0,
            'unique_processed': 0,
            'duplicate_dropped': 0
        }
