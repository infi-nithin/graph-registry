from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import endpoints
from db.database import init_db, close_db
from aop_logging import AOPLoggingMiddleware, RequestTimingMiddleware
from aop_logging import get_aop_logger

logger = get_aop_logger().logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database and run migrations
    logger.info("Initializing database ...")
    await init_db(run_migrations=True)
    yield
    # Shutdown: Close database connections
    logger.info("Close database ...")
    await close_db()


def create_application() -> FastAPI:
    app = FastAPI(
        title="Graph Registry",
        description="Graph Registry API for managing graphs mapped to intents",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(AOPLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(endpoints.router, prefix="/api/v1")

    @app.get("/", tags=["info"])
    async def root():
        return {
            "service": "Graph Registry",
            "version": "0.1.0",
            "description": "Graph Registry API for managing graphs mapped to intents",
            "endpoints": {
                "docs": "/docs",
                "api": "/api/v1",
                "graphs": "/api/v1/graphs",
            },
        }

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
