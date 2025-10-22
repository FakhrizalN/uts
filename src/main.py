"""
Main application entry point.
Initializes and starts the log aggregator service.
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn

from .config import Config
from .dedup_store import DedupStore
from .consumer import Consumer
from .api import create_app

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class Application:
    """Main application class that manages lifecycle of all components"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.consumer: Consumer = None
        self.dedup_store: DedupStore = None
        self.queue: asyncio.Queue = None
        
    async def startup(self):
        """Initialize all components"""
        logger.info("Starting UTS Log Aggregator...")
        
        # Ensure data directory exists
        Config.ensure_data_dir()
        
        # Initialize dedup store
        self.dedup_store = DedupStore(Config.DB_PATH)
        logger.info(f"Dedup store initialized at {Config.DB_PATH}")
        
        # Initialize queue
        self.queue = asyncio.Queue(maxsize=Config.QUEUE_MAX_SIZE)
        logger.info(f"Event queue initialized (max size: {Config.QUEUE_MAX_SIZE})")
        
        # Initialize and start consumer
        self.consumer = Consumer(
            queue=self.queue,
            dedup_store=self.dedup_store,
            batch_size=Config.CONSUMER_BATCH_SIZE,
            sleep_interval=Config.CONSUMER_SLEEP_INTERVAL
        )
        await self.consumer.start()
        
        logger.info(f"Application started successfully at {self.start_time.isoformat()}Z")
    
    async def shutdown(self):
        """Cleanup all components"""
        logger.info("Shutting down UTS Log Aggregator...")
        
        # Stop consumer gracefully
        if self.consumer:
            await self.consumer.stop()
        
        logger.info("Application shutdown complete")


# Global application instance
app_instance = Application()


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager"""
    # Startup
    await app_instance.startup()

    # attach initialized components so endpoints can access them
    app.state.consumer = app_instance.consumer
    app.state.dedup_store = app_instance.dedup_store
    app.state.queue = app_instance.queue
    app.state.start_time = app_instance.start_time

    try:
        yield
    finally:
        # Shutdown
        await app_instance.shutdown()


def create_fastapi_app():
    """Create FastAPI application with lifespan"""
    fastapi_app = create_app(
        consumer=app_instance.consumer,
        dedup_store=app_instance.dedup_store,
        start_time=app_instance.start_time
    )
    fastapi_app.router.lifespan_context = lifespan
    return fastapi_app


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info(f"UTS Log Aggregator v{Config.APP_VERSION}")
    logger.info("Pub-Sub with Idempotent Consumer & Deduplication")
    logger.info("=" * 60)
    
    # Create FastAPI app
    app = create_fastapi_app()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run uvicorn server
    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        log_level=Config.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
