from dataclasses import dataclass, field
from hashlib import md5
from io import BytesIO
import json
from math import isfinite
from pathlib import Path
import wave
from typing import assert_never
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from itchy.game import (
    Broadcast, Message, Arithmetic, ChangeVariable, Command, Comparison, Condition, Costume, Forever,
    Game, GoTo, If, KeyDown, Logic, MoveX, Not, Number, NumberVariable,
    Repeat, RepeatUntil, SetVariable, Sound, PlaySound, Touching, Visibility, Wait, RandomNumber,
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
    shadow: bool = False

    def json(self, index: int) -> dict[str, Json]:
        result: dict[str, Json] = {
            "opcode": self.opcode, "next": self.next, "parent": self.parent,
            "inputs": self.inputs, "fields": self.fields,
            "shadow": self.shadow, "topLevel": self.top_level,
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
    messages = {message.name: message for message in game.messages}
    if len(messages) != len(game.messages):
        raise ValueError("Message names must be unique")
    assets: dict[str, bytes] = {}

    def costume(source: Costume, name: str) -> dict[str, Json]:
        if isinstance(source.svg, Path):
            data = source.svg.read_bytes()
            extension = source.svg.suffix.lower().lstrip(".")
            if extension == "jpeg":
                extension = "jpg"
            if extension not in ("svg", "png", "jpg"):
                raise ValueError(f"Unsupported costume format: {extension}")
        else:
            data = source.svg.encode()
            extension = "svg"
        asset_id = md5(data).hexdigest()
        assets[f"{asset_id}.{extension}"] = data
        return {
            "name": name, "assetId": asset_id, "md5ext": f"{asset_id}.{extension}",
            "dataFormat": extension, "rotationCenterX": source.center_x,
            "rotationCenterY": source.center_y,
        }

    def sound(source: Sound) -> dict[str, Json]:
        data = source.source.read_bytes()
        extension = source.source.suffix.lower().lstrip(".")
        if extension not in ("wav", "mp3"):
            raise ValueError(f"Unsupported sound format: {extension}")
        rate, sample_count = source.rate, source.sample_count
        if extension == "wav":
            with wave.open(BytesIO(data)) as audio:
                rate, sample_count = audio.getframerate(), audio.getnframes()
        asset_id = md5(data).hexdigest()
        assets[f"{asset_id}.{extension}"] = data
        return {"name": source.name, "assetId": asset_id,
                "md5ext": f"{asset_id}.{extension}", "dataFormat": extension,
                "format": "", "rate": rate, "sampleCount": sample_count}

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
        "broadcasts": {f"message:{m.name}": m.name for m in game.messages},
        "blocks": {}, "costumes": [costume(background, "Background")],
        "tempo": 60, "videoTransparency": 50, "videoState": "on",
        "textToSpeechLanguage": None,
    }]
    for sprite in game.sprites:
        blocks: dict[str, Block] = {}
        sound_names = [sound.name for sound in sprite.sounds]
        if len(set(sound_names)) != len(sound_names):
            raise ValueError("Sound names must be unique per sprite")

        def add(
            opcode: str, parent: str | None,
            inputs: dict[str, Json] | None = None,
            fields: dict[str, Json] | None = None, *, top_level: bool = False,
        ) -> str:
            block_id = f"b{len(blocks) + 1}"
            blocks[block_id] = Block(opcode, parent, inputs or {}, fields or {}, top_level=top_level)
            return block_id

        def message_fields(message: Message, field: str) -> dict[str, Json]:
            if messages.get(message.name) is not message:
                raise ValueError(f"Undeclared message: {message.name}")
            return {field: [message.name, f"message:{message.name}"]}

        def variable_fields(variable: NumberVariable) -> dict[str, Json]:
            if declared.get(variable.name) is not variable:
                raise ValueError(f"Undeclared variable: {variable.name}")
            return {"VARIABLE": [variable.name, f"var:{variable.name}"]}

        def numeric(value: Number, parent: str) -> list[Json]:
            if isinstance(value, bool):
                raise TypeError("Boolean literals are not game numbers")
            if isinstance(value, (int, float)):
                return number(value)
            if isinstance(value, NumberVariable):
                reporter = add("data_variable", parent, fields=variable_fields(value))
            elif isinstance(value, RandomNumber):
                reporter = add("operator_random", parent)
                blocks[reporter].inputs = {"FROM": numeric(value.low, reporter), "TO": numeric(value.high, reporter)}
            elif isinstance(value, Arithmetic):
                reporter = add(f"operator_{value.operator}", parent)
                blocks[reporter].inputs = {
                    "NUM1": numeric(value.left, reporter),
                    "NUM2": numeric(value.right, reporter),
                }
            else:
                raise TypeError(f"Unsupported numeric expression: {type(value).__name__}")
            return [3, reporter, [4, "0"]]

        def condition(value: Condition, parent: str) -> list[Json]:
            match value:
                case Comparison(operator, left, right):
                    reporter = add(f"operator_{operator}", parent)
                    blocks[reporter].inputs = {
                        "OPERAND1": numeric(left, reporter), "OPERAND2": numeric(right, reporter),
                    }
                case Logic(operator, left, right):
                    reporter = add(f"operator_{operator}", parent)
                    blocks[reporter].inputs = {
                        "OPERAND1": condition(left, reporter), "OPERAND2": condition(right, reporter),
                    }
                case Not(operand):
                    reporter = add("operator_not", parent)
                    blocks[reporter].inputs = {"OPERAND": condition(operand, reporter)}
                case KeyDown(key):
                    reporter = add("sensing_keypressed", parent)
                    menu = add("sensing_keyoptions", reporter, fields={"KEY_OPTION": [key.value, None]})
                    blocks[menu].shadow = True
                    blocks[reporter].inputs = {"KEY_OPTION": [1, menu]}
                case Touching(target):
                    if target not in names and target not in ("_edge_", "_mouse_"):
                        raise ValueError(f"Unknown touching target: {target}")
                    reporter = add("sensing_touchingobject", parent)
                    menu = add("sensing_touchingobjectmenu", reporter, fields={"TOUCHINGOBJECTMENU": [target, None]})
                    blocks[menu].shadow = True
                    blocks[reporter].inputs = {"TOUCHINGOBJECTMENU": [1, menu]}
                case _:
                    raise TypeError(f"Unsupported condition: {type(value).__name__}")
            return [2, reporter]

        def substack(block_id: str, name: str, body: tuple[Command, ...]) -> None:
            first = sequence(body, block_id)
            if first:
                blocks[block_id].inputs[name] = [2, first]

        def sequence(commands: tuple[Command, ...], parent: str) -> str | None:
            first: str | None = None
            previous: str | None = None
            for command in commands:
                owner = previous or parent
                match command:
                    case GoTo(x, y):
                        block_id = add("motion_gotoxy", owner)
                        blocks[block_id].inputs = {"X": numeric(x, block_id), "Y": numeric(y, block_id)}
                    case MoveX(distance):
                        block_id = add("motion_changexby", owner)
                        blocks[block_id].inputs = {"DX": numeric(distance, block_id)}
                    case SetVariable(variable, value) | ChangeVariable(variable, value):
                        opcode = "data_setvariableto" if isinstance(command, SetVariable) else "data_changevariableby"
                        block_id = add(opcode, owner, fields=variable_fields(variable))
                        blocks[block_id].inputs = {"VALUE": numeric(value, block_id)}
                    case Repeat(times, body):
                        if times < 0:
                            raise ValueError("Repeat count must be nonnegative")
                        block_id = add("control_repeat", owner, {"TIMES": number(times)})
                        substack(block_id, "SUBSTACK", body)
                    case If(predicate, then, otherwise):
                        block_id = add("control_if" if otherwise is None else "control_if_else", owner)
                        blocks[block_id].inputs["CONDITION"] = condition(predicate, block_id)
                        substack(block_id, "SUBSTACK", then)
                        if otherwise is not None:
                            substack(block_id, "SUBSTACK2", otherwise)
                    case Forever(body):
                        block_id = add("control_forever", owner)
                        substack(block_id, "SUBSTACK", body)
                    case RepeatUntil(predicate, body):
                        block_id = add("control_repeat_until", owner)
                        blocks[block_id].inputs["CONDITION"] = condition(predicate, block_id)
                        substack(block_id, "SUBSTACK", body)
                    case Visibility(visible):
                        block_id = add("looks_show" if visible else "looks_hide", owner)
                    case Wait(seconds):
                        block_id = add("control_wait", owner)
                        blocks[block_id].inputs = {"DURATION": numeric(seconds, block_id)}
                    case Broadcast(message, wait):
                        block_id = add("event_broadcastandwait" if wait else "event_broadcast", owner)
                        menu = add("event_broadcast_menu", block_id, fields=message_fields(message, "BROADCAST_OPTION"))
                        blocks[menu].shadow = True
                        blocks[block_id].inputs = {"BROADCAST_INPUT": [1, menu]}
                    case PlaySound(source, wait):
                        if not any(source is declared_sound for declared_sound in sprite.sounds):
                            raise ValueError(f"Undeclared sound: {source.name}")
                        block_id = add("sound_playuntildone" if wait else "sound_play", owner)
                        menu = add("sound_sounds_menu", block_id, fields={"SOUND_MENU": [source.name, None]})
                        blocks[menu].shadow = True
                        blocks[block_id].inputs = {"SOUND_MENU": [1, menu]}
                    case _:
                        assert_never(command)
                if previous:
                    blocks[previous].next = block_id
                if first is None:
                    first = block_id
                previous = block_id
            return first

        for script in sprite.scripts:
            if script.clicked:
                hat = add("event_whenthisspriteclicked", None, top_level=True)
            elif script.message is not None:
                hat = add("event_whenbroadcastreceived", None, fields=message_fields(script.message, "BROADCAST_OPTION"), top_level=True)
            elif script.key is None:
                hat = add("event_whenflagclicked", None, top_level=True)
            else:
                hat = add("event_whenkeypressed", None, fields={"KEY_OPTION": [script.key.value, None]}, top_level=True)
            blocks[hat].next = sequence(script.body, hat)
        targets.append({
            **base, "isStage": False, "name": sprite.name, "variables": {},
            "blocks": {key: block.json(i) for i, (key, block) in enumerate(blocks.items(), 1)},
            "costumes": [costume(c, "Default" if i == 0 else f"Costume {i + 1}") for i, c in enumerate((sprite.costume, *sprite.costumes))],
            "sounds": [sound(s) for s in sprite.sounds],
            "x": sprite.x, "y": sprite.y, "size": 100, "direction": 90,
            "visible": True, "draggable": False, "rotationStyle": "all around",
            "layerOrder": len(targets),
        })
    project: dict[str, Json] = {
        "targets": targets, "monitors": [], "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "itchy"},
    }
    assets["project.json"] = json.dumps(project, allow_nan=False).encode()
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in sorted(assets.items()):
            info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return output.getvalue()
