import asyncio
from contextlib import asynccontextmanager
from threading import Event

from fastapi import FastAPI

from app.api.routes.database import router as database_router
from app.api.routes.orders import router as orders_router
from app.api.routes.customers import router as customers_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.services.outbox_publisher import OutboxPublisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = Event()
    publisher = OutboxPublisher(stop_event)
    publisher_task = asyncio.create_task(asyncio.to_thread(publisher.run))
    yield
    stop_event.set()
    await publisher_task


app = FastAPI(
    title=settings.app_name,
    description="Backend API for an online shop.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(database_router)
app.include_router(orders_router)
app.include_router(customers_router)
