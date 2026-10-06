"""Floor Pulse demo: FastAPI + WebSocket with a dummy-data simulator."""
import asyncio
import contextlib
import json
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .state import FLOORS, Scoreboard

STATIC = Path(__file__).resolve().parent.parent / "static"


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()

    async def broadcast(self, msg: dict) -> None:
        text = json.dumps(msg)
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
            except Exception:
                self.clients.discard(ws)


board = Scoreboard.seeded()
hub = Hub()
simulate = {"on": True}


async def emit_update(event: dict) -> None:
    await hub.broadcast(event)
    await hub.broadcast({"type": "state", **{f: board.view(f) for f in FLOORS}})


async def simulator() -> None:
    """Fake HubSpot/dialer traffic so the screen has something to show."""
    rng = random.Random()
    while True:
        await asyncio.sleep(rng.uniform(1.0, 2.5))
        if not simulate["on"]:
            continue
        agent = rng.choice(list(board.agents))
        if rng.random() < 0.18:
            await emit_update(board.add_deal(agent))
        else:
            await emit_update(board.add_call(agent))


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(simulator())
    yield
    task.cancel()


app = FastAPI(title="Floor Pulse (demo)", lifespan=lifespan)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/state")
def state() -> dict:
    return {f: board.view(f) for f in FLOORS}


def _check(floor: str) -> None:
    if floor not in FLOORS:
        raise HTTPException(404, f"unknown floor {floor}")


@app.post("/demo/deal/{floor}")
async def demo_deal(floor: str) -> dict:
    _check(floor)
    agent = random.choice([a.id for a in board.agents.values() if a.floor == floor])
    ev = board.add_deal(agent)
    await emit_update(ev)
    return ev


@app.post("/demo/recap/{floor}")
async def demo_recap(floor: str) -> dict:
    _check(floor)
    ev = board.recap(floor)
    await hub.broadcast(ev)
    return ev


@app.post("/demo/close/{floor}")
async def demo_close(floor: str) -> dict:
    _check(floor)
    ev = board.close(floor)
    await hub.broadcast(ev)
    return ev


@app.post("/demo/simulator/{flag}")
def demo_sim(flag: str) -> dict:
    simulate["on"] = flag == "on"
    return simulate


@app.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    await websocket.accept()
    hub.clients.add(websocket)
    await websocket.send_text(json.dumps({"type": "state", **{f: board.view(f) for f in FLOORS}}))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.clients.discard(websocket)


app.mount("/static", StaticFiles(directory=STATIC), name="static")
