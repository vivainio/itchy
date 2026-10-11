from dataclasses import replace
from io import BytesIO
import json
from zipfile import ZipFile

import pytest
from itchy.compiler import compile_game
from itchy.game import (
    Argument, Costume, Game, NumberVariable, Procedure, ScratchList, Sprite,
    StringVariable, block, clone, contains, delete_clone, flatten, go_to,
    if_then, join, length, move, move_y, next_costume, on_clone, on_start,
    point_direction, reporter, set_size, switch_costume,
)
from itchy.testing import Flag, Snapshot, Tick, simulate

COSTUME = Costume('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40"/></svg>')


def test_native_lists_strings_motion_and_procedures_in_vm():
    items = ScratchList("items", ("old",))
    text = StringVariable("text")
    count = NumberVariable("count")
    distance = Argument("distance")
    walk = Procedure("walk", (distance,), flatten((move(distance), move_y(3))), warp=True)
    sprite = Sprite("Player", COSTUME, (on_start(
        go_to(0, 0), point_direction(90), walk(12), walk(8),
        items.clear(), items.append("hello"), items.insert(1, "first"),
        items.replace(2, "world"), items.delete(1),
        text.set(join(items.item(1), "!")), count.set(items.length() + length("abc")),
        if_then(contains(text, "world") & items.contains("world"), count.add(10)),
        switch_costume("Costume 2"), next_costume(), set_size(75),
    ),), costumes=(COSTUME,), procedures=(walk,))
    game = Game("Native", (text, count), (sprite,), lists=(items,))
    state = simulate(game, Flag(), Tick(30), Snapshot(("Player",), ("text", "count")))[0]
    assert state["sprites"]["Player"] == {"x": 20, "y": 6}
    assert state["variables"]["text"] == "world!"
    assert float(state["variables"]["count"]) == 14


def test_clones_execute_native_clone_event():
    count = NumberVariable("clones")
    game = Game("Clones", (count,), (Sprite("Player", COSTUME, (
        on_start(clone()), on_clone(count.add(1), delete_clone()),
    )),))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("clones",)))[0]
    assert float(state["variables"]["clones"]) == 1


def test_generic_substacks_extensions_and_mutations():
    count = NumberVariable("count")
    game = Game("Blocks", (count,), (Sprite("Player", COSTUME, (on_start(
        block("control_repeat", inputs={"TIMES": 3}, substacks={"SUBSTACK": flatten((count.add(2),))}),
        block("pen_clear"), count.set(reporter("operator_round", inputs={"NUM": count + 0.4})),
    ),)),), extensions=("pen",))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("count",)))[0]
    assert float(state["variables"]["count"]) == 6
    with ZipFile(BytesIO(compile_game(game))) as archive:
        project = json.loads(archive.read("project.json"))
    assert project["extensions"] == ["pen"]


def test_native_references_are_validated():
    missing = ScratchList("missing")
    game = Game("Invalid", (), (Sprite("Player", COSTUME, (on_start(missing.append("a")),)),))
    with pytest.raises(ValueError, match="Undeclared list"):
        compile_game(game)
    arg = Argument("outside")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(on_start(move(arg)),)),))
    with pytest.raises(ValueError, match="outside its procedure"):
        compile_game(bad)
    proc = Procedure("missing")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(on_start(proc()),)),))
    with pytest.raises(ValueError, match="Undeclared procedure"):
        compile_game(bad)


def test_stage_scripts_and_dynamic_repeat():
    from itchy.game import repeat
    count = NumberVariable("count")
    times = NumberVariable("times", 4)
    game = Game("Stage", (count, times), (), stage=Sprite("Stage", COSTUME, (
        on_start(repeat(times, count.add(1))),
    )))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("count",)))[0]
    assert float(state["variables"]["count"]) == 4


def test_native_string_and_boolean_procedure_arguments():
    from itchy.game import predicate
    text = StringVariable("text")
    word = Argument("word")
    enabled = Argument("enabled", boolean=True)
    proc = Procedure("write", (word, enabled), flatten((
        block("control_if", inputs={"CONDITION": enabled},
              substacks={"SUBSTACK": flatten((text.set(join(word, "!")),))}),
    )))
    game = Game("Arguments", (text,), (Sprite("Player", COSTUME, (
        on_start(proc("hello", predicate("operator_equals", inputs={"OPERAND1": 1, "OPERAND2": 1}))),
    ), procedures=(proc,)),))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("text",)))[0]
    assert state["variables"]["text"] == "hello!"
