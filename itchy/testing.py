"""Typed scenarios sent to the real Scratch VM through its JavaScript runner."""
from dataclasses import dataclass
from base64 import b64encode
from pathlib import Path
import json
import subprocess
from typing import TypedDict

from itchy.compiler import Json, compile_game
from itchy.game import Game
from itchy.setup import ROOT, setup




@dataclass(frozen=True)
class Flag:
    pass


@dataclass(frozen=True)
class Tick:
    count: int = 1


@dataclass(frozen=True)
class Press:
    key: str


@dataclass(frozen=True)
class Release:
    key: str


@dataclass(frozen=True)
class Snapshot:
    sprites: tuple[str, ...] = ()
    variables: tuple[str, ...] = ()


type Step = Flag | Tick | Press | Release | Snapshot


class Position(TypedDict):
    x: float
    y: float


class State(TypedDict):
    sprites: dict[str, Position]
    variables: dict[str, float | str]


def simulate(game: Game, *steps: Step) -> list[State]:
    commands: list[Json] = []
    for step in steps:
        match step:
            case Flag(): commands.append({"op": "flag"})
            case Tick(count): commands.append({"op": "tick", "count": count})
            case Press(key): commands.append({"op": "key", "key": key, "down": True})
            case Release(key): commands.append({"op": "key", "key": key, "down": False})
            case Snapshot(sprites, variables):
                commands.append({"op": "snapshot", "sprites": list(sprites), "variables": list(variables)})
    payload = {"project": b64encode(compile_game(game)).decode(), "steps": commands}
    result = subprocess.run(
        [str(setup()), "runner/scenario.js"], cwd=ROOT,
        input=json.dumps(payload), capture_output=True, text=True, timeout=30, check=True,
    )
    raw: object = json.loads(result.stdout)
    if not isinstance(raw, list):
        raise ValueError("VM runner returned invalid snapshots")
    states: list[State] = []
    for state in raw:
        if not isinstance(state, dict):
            raise ValueError("VM snapshot must be an object")
        positions: dict[str, Position] = {}
        for name, position in state["sprites"].items():
            positions[name] = {"x": float(position["x"]), "y": float(position["y"])}
        values: dict[str, float | str] = {}
        for name, value in state["variables"].items():
            if not isinstance(value, (int, float, str)):
                raise ValueError("VM variable must be numeric or text")
            values[name] = value
        states.append({"sprites": positions, "variables": values})
    return states
