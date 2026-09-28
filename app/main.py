from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import RequestIDMiddleware, setup_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade backend service for EVE Healthcare diagnostic test bookings and simulated payment processing.\n\n"
        "Features:\n"
        "- JWT Authentication & Role-Based Access Control (User/Admin)\n"
        "- Diagnostic Centre & Test Management with Pricing Offerings\n"
        "- Concurrent Booking Slot Reservations & Idempotency Key Handling\n"
        "- Deterministic Payment Gateway Simulation\n"
        "- Idempotent Webhook Processing with HMAC SHA256 Signature Verification\n"
        "- Transactional Audit Logging & Error Standardisation\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
if settings.CORS_ORIGINS:
    origins = (
        [str(origin) for origin in settings.CORS_ORIGINS]
        if isinstance(settings.CORS_ORIGINS, list)
        else [settings.CORS_ORIGINS]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Request ID Correlation Middleware
app.add_middleware(RequestIDMiddleware)

# Custom Standardized Exception Handlers
setup_exception_handlers(app)

# Include Routers
app.include_router(health_router)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "documentation": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
