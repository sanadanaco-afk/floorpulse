"""In-memory scoreboard state (demo). Redis/Postgres replace this later."""
import random
import time
from dataclasses import dataclass, field

FLOORS = ("fr", "es", "it")
TEAMS = ("iOS", "CSS")

DUMMY_NAMES = {
    "fr": ["Camille", "Lucas", "Léa", "Hugo", "Manon", "Théo", "Chloé", "Nathan", "Inès", "Louis"],
    "es": ["Lucía", "Mateo", "Sofía", "Pablo", "Carmen", "Diego", "Valeria", "Álvaro", "Marta", "Jorge"],
    "it": ["Giulia", "Marco", "Sara", "Luca", "Chiara", "Matteo", "Elena", "Andrea", "Francesca", "Paolo"],
}


@dataclass
class Agent:
    id: str
    name: str
    floor: str
    team: str
    deals: int = 0
    calls: int = 0

    def score(self) -> tuple[int, int]:
        return (self.deals, self.calls)


@dataclass
class Scoreboard:
    agents: dict[str, Agent] = field(default_factory=dict)
    last_ranks: dict[str, dict[str, int]] = field(default_factory=dict)

    @classmethod
    def seeded(cls, seed: int | None = None) -> "Scoreboard":
        rng = random.Random(seed)
        sb = cls()
        for floor in FLOORS:
            for i, name in enumerate(DUMMY_NAMES[floor]):
                a = Agent(f"{floor}-{i}", name, floor, TEAMS[i % 2])
                a.deals = rng.randint(0, 3)
                a.calls = rng.randint(5, 40)
                sb.agents[a.id] = a
        sb.snapshot()
        return sb

    def ranking(self, floor: str, team: str | None = None) -> list[Agent]:
        pool = [a for a in self.agents.values() if a.floor == floor and (team is None or a.team == team)]
        return sorted(pool, key=lambda a: (-a.deals, -a.calls, a.name))

    def snapshot(self) -> None:
        self.last_ranks = {
            f: {a.id: r for r, a in enumerate(self.ranking(f), 1)} for f in FLOORS
        }

    def add_deal(self, agent_id: str) -> dict:
        a = self.agents[agent_id]
        a.deals += 1
        return {"type": "deal", "ts": time.time(), "agent": self._dto(a), "floor": a.floor}

    def add_call(self, agent_id: str) -> dict:
        a = self.agents[agent_id]
        a.calls += 1
        return {"type": "call", "ts": time.time(), "agent_id": a.id, "floor": a.floor}

    def recap(self, floor: str) -> dict:
        """Who overtook whom since the last snapshot, then re-snapshot."""
        before = self.last_ranks.get(floor, {})
        now = {a.id: r for r, a in enumerate(self.ranking(floor), 1)}
        moves = []
        for aid, r in now.items():
            if aid in before and r < before[aid]:
                overtaken = [
                    self.agents[o].name for o, ro in before.items()
                    if ro < before[aid] and ro >= r and now[o] > r
                ]
                moves.append({"name": self.agents[aid].name, "from": before[aid], "to": r, "overtook": overtaken})
        moves.sort(key=lambda m: m["from"] - m["to"], reverse=True)
        self.last_ranks[floor] = now
        return {"type": "recap", "floor": floor, "ts": time.time(), "moves": moves[:5],
                "leader": self._dto(self.ranking(floor)[0])}

    def close(self, floor: str) -> dict:
        top = [self._dto(a) for a in self.ranking(floor)[:3]]
        team_deals = {t: sum(a.deals for a in self.ranking(floor, t)) for t in TEAMS}
        pod = max(TEAMS, key=lambda t: team_deals[t])
        return {"type": "close", "floor": floor, "ts": time.time(), "podium": top,
                "pod_of_the_week": {"team": pod, "deals": team_deals[pod]}}

    def view(self, floor: str) -> dict:
        ranks = {a.id: r for r, a in enumerate(self.ranking(floor), 1)}
        return {
            "floor": floor,
            "overall": [self._dto(a, ranks[a.id]) for a in self.ranking(floor)],
            "teams": {t: [self._dto(a, i) for i, a in enumerate(self.ranking(floor, t), 1)] for t in TEAMS},
            "team_totals": {t: sum(a.deals for a in self.ranking(floor, t)) for t in TEAMS},
        }

    @staticmethod
    def _dto(a: Agent, rank: int | None = None) -> dict:
        d = {"id": a.id, "name": a.name, "team": a.team, "floor": a.floor, "deals": a.deals, "calls": a.calls}
        if rank is not None:
            d["rank"] = rank
        return d
