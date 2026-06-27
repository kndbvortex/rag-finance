from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.pdfs import router as pdfs_router
from app.api.v1.stats import router as stats_router
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="RAG — French Public Administration", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(pdfs_router)
app.include_router(stats_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
