import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.database import Base, engine
from app.exceptions import register_exception_handlers
from app.utils.rate_limit import limiter
from app.routes import websocket as ws_route

from app import models  

from app.routes import (
    auth,
    properties,
    buildings,
    units,
    tenants,
    leases,
    rent,
    maintenance,
    utilities,
    visitors,
    parking,
    facilities,
    dashboard,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    description="Smart Property & Facility Management Platform - REST API",
    version="1.0.0",
)


origins = ["*"] if settings.CORS_ORIGINS == "*" else [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)

API_PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(properties.router, prefix=API_PREFIX)
app.include_router(buildings.router, prefix=API_PREFIX)
app.include_router(units.router, prefix=API_PREFIX)
app.include_router(tenants.router, prefix=API_PREFIX)
app.include_router(leases.router, prefix=API_PREFIX)
app.include_router(rent.router, prefix=API_PREFIX)
app.include_router(maintenance.router, prefix=API_PREFIX)
app.include_router(utilities.router, prefix=API_PREFIX)
app.include_router(visitors.router, prefix=API_PREFIX)
app.include_router(parking.router, prefix=API_PREFIX)
app.include_router(facilities.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(ws_route.router)  


@app.on_event("startup")
def on_startup():

    Base.metadata.create_all(bind=engine)
    ws_route.set_loop(asyncio.get_event_loop())


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "app": settings.APP_NAME, "docs": "/docs", "api_prefix": API_PREFIX}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
