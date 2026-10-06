# Floor Pulse (demo)

Real-time, game-style sales scoreboard for the Paris (`fr`), Barcelona (`es`) and Milano (`it`) floors.
**This is a demo running on dummy data** (in-memory, simulated events) to check the look and feel before wiring real sources.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000/?floor=fr   (fr | es | it)
```

A simulator emits fake calls and deals every 1–2.5 s. Buttons in the header trigger the screen moments on demand:

- **Fake deal**: full-screen takeover, confetti, optional sound (click "Sound off" once to enable audio)
- **Hourly recap**: who overtook whom since the last snapshot
- **6PM close**: podium + pod of the week (team with most deals)

The screen shows the floor's overall ranking plus the iOS and CSS rankings, per floor. Country colour themes are applied per floor. The browser reconnects automatically if the WebSocket drops, and shows event-to-screen latency.

## Layout

- `app/state.py`: scoreboard logic (rankings, recap, close)
- `app/main.py`: FastAPI app, WebSocket hub, simulator, `/demo/*` endpoints
- `static/index.html`: kiosk page (single file)
- `tests/`: `pytest`

## Next (real data)

- `POST` ingest for the HubSpot workflow webhook (deal validated = property *Date turned Transferred to CSS* is set) and dialer call events
- Redis for live state, Postgres for history; remove the simulator and `/demo/*`
- Decide how the `global` merged view works
- Monthly themes, weekly pod challenge, p95 < 5 s measurement
