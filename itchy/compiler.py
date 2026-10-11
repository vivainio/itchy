from dataclasses import dataclass, field
from hashlib import md5
from io import BytesIO
import json
from math import isfinite
from typing import assert_never
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from itchy.game import (
    ChangeVariable, Command, Costume, Game, GoTo, MoveX, Repeat, SetVariable,
)

type Json = None | bool | int | float | str | list[Json] | dict[str, Json]


def number(value: float) -> list[Json]:
    if not isfinite(value):
        raise ValueError("Numbers must be finite")
    return [1, [4, str(value)]]


@dataclass
class Block:
    opcode: str
    parent: str | None
    inputs: dict[str, Json] = field(default_factory=dict)
    fields: dict[str, Json] = field(default_factory=dict)
    next: str | None = None
    top_level: bool = False

    def json(self, index: int) -> dict[str, Json]:
        result: dict[str, Json] = {
            "opcode": self.opcode, "next": self.next, "parent": self.parent,
            "inputs": self.inputs, "fields": self.fields,
            "shadow": False, "topLevel": self.top_level,
        }
        if self.top_level:
            result.update(x=40, y=index * 80)
        return result


def compile_game(game: Game) -> bytes:
    names = [sprite.name for sprite in game.sprites]
    if len(set(names)) != len(names) or "Stage" in names:
        raise ValueError("Sprite names must be unique and cannot be Stage")
    declared = {variable.name: variable for variable in game.variables}
    if len(declared) != len(game.variables):
        raise ValueError("Variable names must be unique")
    for variable in game.variables:
        number(variable.initial)
    assets: dict[str, str] = {}

    def costume(source: Costume, name: str) -> dict[str, Json]:
        asset_id = md5(source.svg.encode()).hexdigest()
        assets[f"{asset_id}.svg"] = source.svg
        return {
            "name": name, "assetId": asset_id, "md5ext": f"{asset_id}.svg",
            "dataFormat": "svg", "rotationCenterX": source.center_x,
            "rotationCenterY": source.center_y,
        }

    base: dict[str, Json] = {
        "lists": {}, "broadcasts": {}, "comments": {},
        "currentCostume": 0, "sounds": [], "volume": 100,
    }
    background = Costume(
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
        '<rect width="480" height="360" fill="#eef2ff"/></svg>', 240, 180,
    )
    targets: list[Json] = [{
        **base, "isStage": True, "name": "Stage",
        "variables": {f"var:{v.name}": [v.name, v.initial] for v in game.variables},
        "blocks": {}, "costumes": [costume(background, "Background")],
        "tempo": 60, "videoTransparency": 50, "videoState": "on",
        "textToSpeechLanguage": None,
    }]
    for sprite in game.sprites:
        blocks: dict[str, Block] = {}

        def add(
            opcode: str, parent: str | None,
            inputs: dict[str, Json] | None = None,
            fields: dict[str, Json] | None = None, *, top_level: bool = False,
        ) -> str:
            block_id = f"b{len(blocks) + 1}"
            blocks[block_id] = Block(opcode, parent, inputs or {}, fields or {}, top_level=top_level)
            return block_id

        def sequence(commands: tuple[Command, ...], parent: str) -> str | None:
            first: str | None = None
            previous: str | None = None
            for command in commands:
                owner = previous or parent
                match command:
                    case GoTo(x, y):
                        block_id = add("motion_gotoxy", owner, {"X": number(x), "Y": number(y)})
                    case MoveX(distance):
                        block_id = add("motion_changexby", owner, {"DX": number(distance)})
                    case SetVariable(variable, value) | ChangeVariable(variable, value):
                        if declared.get(variable.name) is not variable:
                            raise ValueError(f"Undeclared variable: {variable.name}")
                        opcode = "data_setvariableto" if isinstance(command, SetVariable) else "data_changevariableby"
                        block_id = add(opcode, owner, {"VALUE": number(value)}, {"VARIABLE": [variable.name, f"var:{variable.name}"]})
                    case Repeat(times, body):
                        if times < 0:
                            raise ValueError("Repeat count must be nonnegative")
                        block_id = add("control_repeat", owner, {"TIMES": number(times)})
                        substack = sequence(body, block_id)
                        if substack:
                            blocks[block_id].inputs["SUBSTACK"] = [2, substack]
                    case _:
                        assert_never(command)
                if previous:
                    blocks[previous].next = block_id
                if first is None:
                    first = block_id
                previous = block_id
            return first

        for script in sprite.scripts:
            if script.key is None:
                hat = add("event_whenflagclicked", None, top_level=True)
            else:
                hat = add("event_whenkeypressed", None, fields={"KEY_OPTION": [script.key.value, None]}, top_level=True)
            blocks[hat].next = sequence(script.body, hat)
        targets.append({
            **base, "isStage": False, "name": sprite.name, "variables": {},
            "blocks": {key: block.json(i) for i, (key, block) in enumerate(blocks.items(), 1)},
            "costumes": [costume(sprite.costume, "Default")],
            "x": sprite.x, "y": sprite.y, "size": 100, "direction": 90,
            "visible": True, "draggable": False, "rotationStyle": "all around",
            "layerOrder": len(targets),
        })
    project: dict[str, Json] = {
        "targets": targets, "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "itchy"},
    }
    assets["project.json"] = json.dumps(project, allow_nan=False)
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in sorted(assets.items()):
            info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return output.getvalue()
