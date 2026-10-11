from itchy import control, events, looks, operators
from itchy.control import if_
from itchy import move
from dataclasses import replace
from io import BytesIO
import json
from zipfile import ZipFile

import pytest
from itchy.compiler import compile_game
from itchy.game import Argument, Costume, Game, Num, Procedure, ScratchList, Sprite, String, block, flatten, reporter
from itchy.testing import Flag, Snapshot, Tick, simulate

COSTUME = Costume('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40"/></svg>')


def test_variadic_join_preserves_binary_block_structure():
    from dataclasses import asdict

    value = String("value")
    assert asdict(operators.join(value, ";", 12, ";", "end")) == asdict(
        operators.join(operators.join(operators.join(operators.join(value, ";"), 12), ";"), "end")
    )


def test_native_lists_strings_motion_and_procedures_in_vm():
    items = ScratchList("items", ("old",))
    text = String("text")
    count = Num("count")
    distance = Argument("distance")
    walk = Procedure("walk", (distance,), flatten((move.steps(distance), move.y(3))), warp=True)
    sprite = Sprite("Player", COSTUME, (events.on_start(
        move.to(0, 0), move.point_direction(90), walk(12), walk(8),
        items.clear(), items.append("hello"), items.insert(1, "first"),
        items.replace(2, "world"), items.delete(1),
        text.set(operators.join(items.item(1), "!")), count.set(items.length() + operators.length("abc")),
        control.if_then(operators.contains(text, "world") & items.contains("world"), count.add(10)),
        looks.switch_costume("Costume 2"), looks.next_costume(), looks.set_size(75),
    ),), costumes=(COSTUME,), procedures=(walk,))
    game = Game("Native", (text, count), (sprite,), lists=(items,))
    state = simulate(game, Flag(), Tick(30), Snapshot(("Player",), ("text", "count")))[0]
    assert state["sprites"]["Player"] == {"x": 20, "y": 6}
    assert state["variables"]["text"] == "world!"
    assert float(state["variables"]["count"]) == 14


def test_clones_execute_native_clone_event():
    count = Num("clones")
    game = Game("Clones", (count,), (Sprite("Player", COSTUME, (
        events.on_start(control.clone()), events.on_clone(count.add(1), control.delete_clone()),
    )),))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("clones",)))[0]
    assert float(state["variables"]["clones"]) == 1


def test_generic_substacks_extensions_and_mutations():
    count = Num("count")
    game = Game("Blocks", (count,), (Sprite("Player", COSTUME, (events.on_start(
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
    game = Game("Invalid", (), (Sprite("Player", COSTUME, (events.on_start(missing.append("a")),)),))
    with pytest.raises(ValueError, match="Undeclared list"):
        compile_game(game)
    arg = Argument("outside")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(events.on_start(move.steps(arg)),)),))
    with pytest.raises(ValueError, match="outside its procedure"):
        compile_game(bad)
    proc = Procedure("missing")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(events.on_start(proc()),)),))
    with pytest.raises(ValueError, match="Undeclared procedure"):
        compile_game(bad)


def test_stage_scripts_and_dynamic_repeat():
    count = Num("count")
    times = Num("times", 4)
    game = Game("Stage", (count, times), (), stage=Sprite("Stage", COSTUME, (
        events.on_start(control.repeat(times, count.add(1))),
    )))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("count",)))[0]
    assert float(state["variables"]["count"]) == 4


def test_native_string_and_boolean_procedure_arguments():
    from itchy.game import predicate
    text = String("text")
    word = Argument("word")
    enabled = Argument("enabled", boolean=True)
    proc = Procedure("write", (word, enabled), flatten((
        block("control_if", inputs={"CONDITION": enabled},
              substacks={"SUBSTACK": flatten((text.set(operators.join(word, "!")),))}),
    )))
    game = Game("Arguments", (text,), (Sprite("Player", COSTUME, (
        events.on_start(proc("hello", predicate("operator_equals", inputs={"OPERAND1": 1, "OPERAND2": 1}))),
    ), procedures=(proc,)),))
    state = simulate(game, Flag(), Tick(20), Snapshot(variables=("text",)))[0]
    assert state["variables"]["text"] == "hello!"


def test_procedure_decorator_preserves_custom_blocks_and_forward_calls():
    from itchy.game import procedure

    @procedure(warp=True, proccode='walk %s', argument_names=('Distance',),
               argument_ids=('distance-id',), argument_defaults=('10',))
    def walk(distance):
        return advance(distance)

    @procedure()
    def advance(distance):
        return move.steps(distance)

    game = Game('Decorated', (), (Sprite('Player', COSTUME, (
        events.on_start(move.point_direction(90), walk(12)),
    ), procedures=(walk, advance)),))
    state = simulate(game, Flag(), Tick(10), Snapshot(('Player',)))[0]
    assert state['sprites']['Player']['x'] == 12
    assert walk.arguments[0].name == 'Distance'
    with ZipFile(BytesIO(compile_game(game))) as archive:
        project = json.loads(archive.read('project.json'))
    blocks = project['targets'][1]['blocks'].values()
    prototype = next(block for block in blocks if block['opcode'] == 'procedures_prototype'
                     and block['mutation']['proccode'] == 'walk %s')
    assert prototype['mutation']['warp'] == 'true'
    assert json.loads(prototype['mutation']['argumentids']) == ['distance-id']
    assert json.loads(prototype['mutation']['argumentdefaults']) == ['10']


def test_procedure_decorator_supports_recursion_and_boolean_parameters():
    from itchy.game import Condition, procedure

    @procedure(warp=True)
    def recursive(distance):
        return if_(distance > 0).then_(move.steps(distance), recursive(distance - 1))

    @procedure()
    def choose(enabled: Condition):
        return if_(enabled).then_(move.steps(5))

    game = Game('Recursive', (), (Sprite('Player', COSTUME, (
        events.on_start(move.point_direction(90), recursive(3), choose(reporter('operator_equals',
            inputs={'OPERAND1': 1, 'OPERAND2': 1}))),
    ), procedures=(recursive, choose)),))
    state = simulate(game, Flag(), Tick(30), Snapshot(('Player',)))[0]
    assert state['sprites']['Player']['x'] == 11
    assert choose.arguments[0].boolean
