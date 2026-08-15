"""
FastAPI app wrapping the engine. Not wired up until Phase 3 -- the engine
needs to actually work standalone (Phase 0-2) before it's worth exposing
over HTTP.
"""

from fastapi import FastAPI

app = FastAPI(title="Bughouse Bot API")


@app.get("/health")
def health():
    return {"status": "ok"}
