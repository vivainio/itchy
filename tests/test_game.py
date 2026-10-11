from dataclasses import replace
from io import BytesIO
import json
from zipfile import ZipFile

import pytest
from games.coin_runner import game, player_costume
from itchy.compiler import compile_game
from itchy.game import Game, Num, Sprite, action, go_to, move_x, on_start, repeat
from itchy.testing import Flag, Press, Release, Snapshot, Tick, simulate


def test_movement_scoring_release_restart() -> None:
    snapshot = Snapshot(("Player",), ("score",))
    states = simulate(
        game, Flag(), Tick(2), snapshot,
        Press("ArrowRight"), Tick(2), snapshot,
        Release("ArrowRight"), Tick(2), snapshot,
        Press("ArrowLeft"), Tick(2), Release("ArrowLeft"), snapshot,
        Press(" "), Tick(2), Release(" "), Press(" "), Tick(2), Release(" "), snapshot,
        Press("ArrowRight"), Tick(2), Release("ArrowRight"), Flag(), Tick(2), snapshot,
    )
    assert [state["sprites"]["Player"]["x"] for state in states] == [0, 10, 10, 0, 0, 0]
    assert [float(state["variables"]["score"]) for state in states] == [0, 0, 0, 0, 2, 0]


def test_nested_generated_actions() -> None:
    points = Num("points", 7)

    @action
    def stride(distance: float, count: int):
        return repeat(count, move_x(distance), points.add(1))

    generated = Game("Generated", (points,), (Sprite(
        "Walker", player_costume,
        (on_start(go_to(0, 0), points.reset(), [stride(4, 3), stride(-2, 2)],
                  repeat(2, repeat(2, move_x(1)))),),
    ),))
    state = simulate(generated, Flag(), Tick(40), Snapshot(("Walker",), ("points",)))[0]
    assert state["sprites"]["Walker"]["x"] == 12
    assert float(state["variables"]["points"]) == 12


def test_undeclared_variable_is_rejected() -> None:
    missing = Num("missing")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(on_start(missing.set(1)),)),))
    with pytest.raises(ValueError, match="Undeclared variable"):
        compile_game(bad)


def test_export_is_deterministic_and_contains_assets() -> None:
    exported = compile_game(game)
    assert exported == compile_game(game)
    with ZipFile(BytesIO(exported)) as archive:
        project = json.loads(archive.read("project.json"))
        assert project["extensions"] == []
        for target in project["targets"]:
            for costume in target["costumes"]:
                assert costume["md5ext"] in archive.namelist()
