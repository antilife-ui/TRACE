import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as core_router
from app.api.dashboard_routes import router as dashboard_router
from app.core import config as cfg
from app.core.model_registry import registry
from app.core.live_engine import engine, start_ticker

app = FastAPI(title="TRACE Backend Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    registry.load(checkpoint_path=cfg.CHECKPOINT_PATH, scaler_path=cfg.SCALER_PATH)
    # Streams the dataset once and builds the in-memory state timeline the
    # dashboard polls. Blocking here (rather than backgrounding it) means the
    # server doesn't report "ready" for endpoints that need it before it
    # actually is; see app/core/live_engine.py for the row cap / timing notes.
    engine.build()
    asyncio.create_task(start_ticker())


# Core ML API (health, POST /forecast|/rollout|/explain, low-level model status).
app.include_router(core_router)

# Dashboard-shaped API the frontend's src/api/*.js files call.
app.include_router(dashboard_router, prefix="/api")
