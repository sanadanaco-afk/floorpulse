from fastapi.testclient import TestClient

from app.main import app, simulate
from app.state import Scoreboard


def test_ranking_orders_by_deals_then_calls():
    sb = Scoreboard.seeded(1)
    sb.add_deal("fr-3")
    sb.add_deal("fr-3")
    sb.agents["fr-3"].deals += 10
    assert sb.ranking("fr")[0].id == "fr-3"


def test_close_has_podium_and_pod():
    ev = Scoreboard.seeded(2).close("es")
    assert len(ev["podium"]) == 3 and ev["pod_of_the_week"]["team"] in ("iOS", "CSS")


def test_recap_reports_overtake():
    sb = Scoreboard.seeded(3)
    last = sb.ranking("it")[-1]
    last.deals += 50
    ev = sb.recap("it")
    assert ev["moves"][0]["name"] == last.name and ev["moves"][0]["to"] == 1


def test_http_and_ws():
    simulate["on"] = False
    with TestClient(app) as c:
        assert c.get("/").status_code == 200
        assert set(c.get("/api/state").json()) == {"fr", "es", "it"}
        with c.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "state"
            assert c.post("/demo/deal/fr").status_code == 200
            assert ws.receive_json()["type"] == "deal"
        assert c.post("/demo/deal/xx").status_code == 404
