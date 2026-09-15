from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine, ensure_schema
from app.routers.api import router as api_router
from app.seed import seed_if_empty

Base.metadata.create_all(bind=engine)
ensure_schema()


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


run_seed()


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


@app.get("/api/health")
def health():
    return {"ok": True, "service": "hetu"}
