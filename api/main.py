from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine.board import BughouseGame

app = FastAPI(title="Bughouse Bot API")

# Local dev frontend runs on a different port than the API -- browsers
# block cross-origin requests by default without this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["GET"],
    allow_headers=["*"],
)

GAMES_DIR = Path("saved_games")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/games")
def list_games():
    """the frontend uses these as IDs to request a specific game's frames."""
    if not GAMES_DIR.exists():
        return {"games": []}
    return {"games": sorted(p.stem for p in GAMES_DIR.glob("*.json"))}

def _summarize_outcome(game: BughouseGame):
    over, res = game.winner()
    if not over:
        return {"status": "in progress"}
    return {"status": res}

@app.get("/games/{game_id}/frames")
def get_game_frames(game_id: str):
    """
    Gets the board frames to render in the front-end
    """
    path = GAMES_DIR / f"{game_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"no saved game '{game_id}'")

    try:
        san_log_a, san_log_b = BughouseGame.load_game_logs(str(path))
    except (OSError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"couldn't read '{game_id}': {e}")

    game = BughouseGame()
    try:
        frames = game.replay_with_frames(san_log_a, san_log_b)
    except Exception as e:
        # a corrupted or hand-edited log shouldn't crash the server
        raise HTTPException(status_code=500, detail=f"replay failed for '{game_id}': {e}")

    return {
        "game_id": game_id,
        "frame_count": len(frames),
        "outcome": _summarize_outcome(game),
        "frames": frames,
    }
