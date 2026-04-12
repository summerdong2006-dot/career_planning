from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.assistant import router as assistant_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.job_graph import router as job_graph_router
from app.api.routes.job_profiles import router as job_profile_router
from app.api.routes.matching import router as matching_router
from app.api.routes.portal import router as portal_router
from app.api.routes.reports import router as report_router
from app.api.routes.resumes import router as resume_router
from app.api.routes.student_profiles import router as student_profile_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import check_database_connection
from app.db.session import SessionLocal
from app.modules.job_profile.demo_seed import seed_demo_job_profiles_if_needed

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    if not settings.skip_db_check:
        db_ok = await check_database_connection()
        if not db_ok:
            raise RuntimeError("Database connection failed during startup")
    if settings.demo_auto_seed_job_profiles:
        async with SessionLocal() as session:
            await seed_demo_job_profiles_if_needed(
                session=session,
                seed_path=settings.demo_job_seed_path,
            )
    yield
    logger.info("Stopping %s", settings.app_name)



def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(assistant_router)
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(job_profile_router)
    app.include_router(job_graph_router)
    app.include_router(student_profile_router)
    app.include_router(matching_router)
    app.include_router(portal_router)
    app.include_router(report_router)
    app.include_router(resume_router)
    return app


app = create_app()
