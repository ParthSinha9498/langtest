from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from langtest_server.settings import load_settings
from langtest_server.threads import router as threads_router
from langtest_server.topology import router as topology_router

app = FastAPI(title="LangTest Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(threads_router)
app.include_router(topology_router)


@app.get("/health")
def health() -> dict:
    settings = load_settings()
    return {"status": "ok", "db_path": settings.db_path}
