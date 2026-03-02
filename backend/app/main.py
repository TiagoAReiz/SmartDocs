import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from loguru import logger

from app.api import auth, documents, chat, admin, admin_audit
from app.core.exceptions import generic_exception_handler


def configure_logging():
    """Configure loguru for structured logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        level="INFO",
        colorize=True,
    )
    logger.add(
        "logs/smartdocs.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    configure_logging()
    logger.info("🚀 SmartDocs API starting up...")
    yield
    logger.info("👋 SmartDocs API shutting down...")


def create_app() -> FastAPI:
    """Application factory."""
    application = FastAPI(
        title="SmartDocs API",
        description="Sistema de gestão de documentos inteligente com chat SQL",
        version="1.0.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "https://lemon-glacier-04e92850f.2.azurestaticapps.net",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    application.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    application.include_router(auth.router)
    application.include_router(documents.router)
    application.include_router(chat.router)
    application.include_router(admin.router)
    application.include_router(admin_audit.router)

    @application.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "service": "smartdocs-api"}

    return application


app = create_app()
