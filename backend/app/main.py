from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.document_routes import router as document_router
from app.database import Base, SessionLocal, engine, ensure_schema
from app.routers.api import router as api_router
from app.routers.care import router as care_router
from app.seed import purge_demo_accounts
from app.storage import ensure_reports_dir
from logic.flag_detection import refresh_fallback_flags
from logic.report_conflict import backfill_senior_review_credits

Base.metadata.create_all(bind=engine)
ensure_schema()
ensure_reports_dir()


def run_seed() -> None:
    db = SessionLocal()
    try:
        purge_demo_accounts(db)
        backfill_senior_review_credits(db)
        if refresh_fallback_flags(db):
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_seed()
    yield


app = FastAPI(title="Hetu", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")
app.include_router(care_router, prefix="/api")
app.include_router(document_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True, "service": "hetu"}
