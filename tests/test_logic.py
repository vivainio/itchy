from itchy import control, events, sensing
from itchy.control import if_
from itchy import move
from dataclasses import replace

import pytest
from games.coin_runner import player_costume
from itchy.compiler import compile_game
from itchy.game import Condition, Game, Key, Num, Sprite
from itchy.testing import Flag, Press, Release, Snapshot, Tick, simulate


def test_arithmetic_branching_and_repeat_until() -> None:
    count = Num("count")
    result = Num("result")
    game = Game("Logic", (count, result), (Sprite("Player", player_costume, (
        events.on_start(
            count.reset(), result.reset(),
            control.repeat_until(count >= 3, count.add(1)),
            if_((count.equals(3) & ~(count < 0)) | (count > 10))
                .then_([result.set((count * 4 + 6) / 2 - 1)])
                .else_([result.set(-100)]),
            control.if_then(count <= 3, move.x(result)),
            if_(count < 0).then_(result.set(-200)).else_(result.add(2)),
            control.if_then(count > 100, result.set(-300)),
        ),
    )),))
    state = simulate(game, Flag(), Tick(30), Snapshot(("Player",), ("count", "result")))[0]
    assert state["sprites"]["Player"]["x"] == 8
    assert float(state["variables"]["count"]) == 3
    assert float(state["variables"]["result"]) == 10


def test_forever_reacts_to_key_state_and_releases() -> None:
    count = Num("count")
    game = Game("Continuous", (count,), (Sprite("Player", player_costume, (
        events.on_start(move.to(0, 0), control.forever(control.if_then(sensing.key_down(Key.RIGHT), move.x(2)))),
    )),))
    snap = Snapshot(("Player",))
    states = simulate(game, Flag(), Tick(5), snap, Press("ArrowRight"), Tick(10), snap,
                      Release("ArrowRight"), Tick(3), snap, Tick(10), snap)
    assert states[0]["sprites"]["Player"]["x"] == 0
    assert states[1]["sprites"]["Player"]["x"] > 0
    assert states[2]["sprites"]["Player"]["x"] == states[3]["sprites"]["Player"]["x"]


def test_conditions_cannot_accidentally_run_in_python() -> None:
    count = Num("count")
    condition: Condition = count > 0
    with pytest.raises(TypeError, match="build time"):
        bool(condition)
    with pytest.raises(TypeError, match="build time"):
        bool(count + 1)


def test_reporter_references_are_validated() -> None:
    count = Num("count")
    unknown = Num("unknown")
    game = Game("Invalid", (count,), (Sprite("Player", player_costume, (
        events.on_start(control.if_then(unknown > 0, count.add(1))),
    )),))
    with pytest.raises(ValueError, match="Undeclared variable"):
        compile_game(game)
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(
        events.on_start(control.if_then(sensing.touching("Missing"), count.add(1))),
    )),))
    with pytest.raises(ValueError, match="Unknown touching target"):
        compile_game(bad)


@pytest.mark.parametrize('value, expected', [(0, 10), (1, 20), (2, 30), (3, 40)])
def test_elif_chain_selects_one_branch(value, expected):
    count = Num('count', value)
    result = Num('result')
    first = if_(count.equals(0)).then_(result.set(10))
    chain = (first.elif_(count.equals(1)).then_(result.set(20))
             .elif_(count.equals(2)).then_(result.set(30))
             .else_(result.set(40)))
    assert first.otherwise is None
    game = Game('Branches', (count, result), (Sprite('Player', player_costume, (
        events.on_start(chain),
    )),))
    compile_game(game)
    state = simulate(game, Flag(), Tick(10), Snapshot((), ('result',)))[0]
    assert float(state['variables']['result']) == expected
