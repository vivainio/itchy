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
    NativeCommand, NativeReporter, NativeCondition, Menu, Value, FieldValue,
    StringVariable, ScratchList, Argument, Procedure, ProcedureCall,
    Broadcast, Message, Arithmetic, ChangeVariable, Command, Comparison, Condition, Costume, Forever,
    Game, GoTo, If, Key, KeyDown, Logic, MoveX, Not, Number, NumberVariable,
    Repeat, RepeatUntil, SetVariable, Sound, PlaySound, Touching, Visibility, Wait, RandomNumber, ScratchLiteral,
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
    mutation: dict[str, Json] | None = None

    def json(self, index: int) -> dict[str, Json]:
        result: dict[str, Json] = {
            "opcode": self.opcode, "next": self.next, "parent": self.parent,
            "inputs": self.inputs, "fields": self.fields,
            "shadow": self.shadow, "topLevel": self.top_level,
        }
        if self.mutation is not None:
            result["mutation"] = self.mutation
        if self.top_level:
            result.update(x=40, y=index * 80)
        return result


def compile_game(game: Game) -> bytes:
    names = [sprite.name for sprite in game.sprites]
    if len(set(names)) != len(names) or "Stage" in names:
        raise ValueError("Sprite names must be unique and cannot be Stage")
    all_variables = (*game.variables, *(variable for sprite in game.sprites for variable in sprite.variables),
                     *((variable for variable in game.stage.variables) if game.stage is not None else ()))
    if len({variable.name for variable in all_variables}) != len(all_variables) and any(variable.id is None for variable in all_variables):
        raise ValueError("Variable names must be unique unless explicit Scratch ids are used")
    declared = {id(variable): variable for variable in all_variables}
    for variable in all_variables:
        if isinstance(variable, NumberVariable):
            number(variable.initial)
    messages = {message.name: message for message in game.messages}
    if len(messages) != len(game.messages):
        raise ValueError("Message names must be unique")
    all_lists = (*game.lists, *(item for sprite in game.sprites for item in sprite.lists),
                 *((item for item in game.stage.lists) if game.stage is not None else ()))
    lists = {id(item): item for item in all_lists}
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
            "name": source.name or name, "assetId": asset_id, "md5ext": f"{asset_id}.{extension}",
            "dataFormat": extension, "bitmapResolution": source.bitmap_resolution,
            "rotationCenterX": source.center_x,
            "rotationCenterY": source.center_y,
        }

    def sound(source: Sound) -> dict[str, Json]:
        data = source.source.read_bytes()
        extension = source.source.suffix.lower().lstrip(".")
        if extension not in ("wav", "mp3"):
            raise ValueError(f"Unsupported sound format: {extension}")
        rate, sample_count = source.rate, source.sample_count
        if extension == "wav":
            try:
                with wave.open(BytesIO(data)) as audio:
                    rate, sample_count = audio.getframerate(), audio.getnframes()
            except wave.Error:
                # Scratch archives may contain compressed WAV variants such as ADPCM.
                pass
        asset_id = md5(data).hexdigest()
        assets[f"{asset_id}.{extension}"] = data
        return {"name": source.name, "assetId": asset_id,
                "md5ext": f"{asset_id}.{extension}", "dataFormat": extension,
                "format": source.format, "rate": rate, "sampleCount": sample_count}

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
        "variables": {v.id or f"var:{v.name}": [v.name, v.initial] for v in game.variables},
        "broadcasts": {m.id or f"message:{m.name}": m.name for m in game.messages},
        "lists": {item.id or f"list:{item.name}": [item.name, list(item.initial)] for item in game.lists},
        "blocks": {}, "costumes": [costume(background, "Background")],
        "tempo": game.tempo, "videoTransparency": game.video_transparency, "videoState": game.video_state,
        "textToSpeechLanguage": game.text_to_speech_language,
    }]
    for sprite in (*game.sprites, *((game.stage,) if game.stage is not None else ())):
        is_stage = sprite is game.stage
        blocks: dict[str, Block] = {}
        sound_names = [sound.name for sound in sprite.sounds]
        if len(set(sound_names)) != len(sound_names):
            raise ValueError("Sound names must be unique per sprite")

        def add(
            opcode: str, parent: str | None,
            inputs: dict[str, Json] | None = None,
            fields: dict[str, Json] | None = None, *, top_level: bool | None = None,
        ) -> str:
            block_id = f"b{len(blocks) + 1}"
            blocks[block_id] = Block(
                opcode, parent, inputs or {}, fields or {},
                top_level=parent is None if top_level is None else top_level,
            )
            return block_id

        def message_fields(message: Message, field: str) -> dict[str, Json]:
            if messages.get(message.name) is not message:
                raise ValueError(f"Undeclared message: {message.name}")
            return {field: [message.name, message.id or f"message:{message.name}"]}

        def variable_fields(variable: NumberVariable | StringVariable) -> dict[str, Json]:
            if declared.get(id(variable)) is not variable:
                raise ValueError(f"Undeclared variable: {variable.name}")
            return {"VARIABLE": [variable.name, variable.id or f"var:{variable.name}"]}

        procedures = {id(proc): proc for proc in sprite.procedures}
        if len({proc.proccode or proc.name for proc in sprite.procedures}) != len(sprite.procedures):
            raise ValueError("Procedure names must be unique per sprite")
        active_procedure: Procedure | None = None

        def native_fields(fields: dict[str, FieldValue]) -> dict[str, Json]:
            result: dict[str, Json] = {}
            for key, value in fields.items():
                if isinstance(value, (NumberVariable, StringVariable)):
                    result[key] = variable_fields(value)["VARIABLE"]
                elif isinstance(value, ScratchList):
                    if lists.get(id(value)) is not value:
                        raise ValueError(f"Undeclared list: {value.name}")
                    result[key] = [value.name, value.id or f"list:{value.name}"]
                else:
                    result[key] = [value, None]
            return result

        def native_inputs(inputs: dict[str, Value | Menu], parent: str) -> dict[str, Json]:
            return {key: value_input(value, parent) for key, value in inputs.items()}

        def value_input(value: Value | Menu, parent: str) -> list[Json]:
            if isinstance(value, Menu):
                menu = add(value.opcode, parent, fields={value.field: [value.value, value.id]})
                blocks[menu].shadow = True
                return [1, menu]
            if isinstance(value, ScratchLiteral):
                literal: list[Json] = [value.type, value.value]
                if value.id is not None:
                    literal.append(value.id)
                return [1, literal]
            if isinstance(value, str):
                return [1, [10, value]]
            if isinstance(value, (NativeReporter, NativeCondition)):
                node = add(value.opcode, parent, fields=native_fields(value.fields))
                blocks[node].inputs = native_inputs(value.inputs, node)
                return [2, node] if isinstance(value, NativeCondition) else [3, node, [10, ""]]
            if isinstance(value, Condition):
                return condition(value, parent)
            if isinstance(value, StringVariable):
                node = add("data_variable", parent, fields=variable_fields(value))
                return [3, node, [10, ""]]
            if isinstance(value, ScratchList):
                node = add("data_listcontents", parent, fields=native_fields({"LIST": value}))
                return [3, node, [10, ""]]
            if isinstance(value, Argument):
                if not value.imported and (active_procedure is None or not any(value is arg for arg in active_procedure.arguments)):
                    raise ValueError(f"Argument outside its procedure: {value.name}")
                node = add("argument_reporter_boolean" if value.boolean else "argument_reporter_string_number",
                           parent, fields={"VALUE": [value.name, None]})
                return [2, node] if value.boolean else [3, node, [10, ""]]
            if isinstance(value, Condition):
                return condition(value, parent)
            return numeric(value, parent)

        def procedure_mutation(proc: Procedure, *, prototype: bool = False) -> dict[str, Json]:
            result: dict[str, Json] = {
                "tagName": "mutation", "children": [],
                "proccode": proc.proccode or proc.name + "".join(" %b" if arg.boolean else " %s" for arg in proc.arguments),
                "argumentids": json.dumps(proc.argument_ids or [f"arg:{i}" for i in range(len(proc.arguments))]),
                "warp": "true" if proc.warp else "false",
            }
            if prototype:
                result["argumentnames"] = json.dumps([arg.name for arg in proc.arguments])
                result["argumentdefaults"] = json.dumps(
                    proc.argument_defaults or [False if arg.boolean else "" for arg in proc.arguments]
                )
            return result

        def numeric(value: Number, parent: str) -> list[Json]:
            if isinstance(value, (NativeReporter, Argument)):
                return value_input(value, parent)
            if isinstance(value, NativeCondition):
                return value_input(value, parent)
            if isinstance(value, Condition):
                return condition(value, parent)
            if isinstance(value, ScratchLiteral):
                literal: list[Json] = [value.type, value.value]
                if value.id is not None:
                    literal.append(value.id)
                return [1, literal]
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
            if isinstance(value, (NativeCondition, NativeReporter, Argument, ScratchLiteral,
                                  NumberVariable, StringVariable, ScratchList, str)):
                return value_input(value, parent)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return number(value)
            if isinstance(value, (Arithmetic, RandomNumber)):
                return numeric(value, parent)
            match value:
                case Comparison(operator, left, right):
                    reporter = add(f"operator_{operator}", parent)
                    blocks[reporter].inputs = {
                        "OPERAND1": value_input(left, reporter), "OPERAND2": value_input(right, reporter),
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
                    key_value = key.value if isinstance(key, Key) else key
                    menu = add("sensing_keyoptions", reporter, fields={"KEY_OPTION": [key_value, None]})
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

        def sequence(commands: tuple[Command, ...], parent: str | None) -> str | None:
            first: str | None = None
            previous: str | None = None
            for command in commands:
                owner = previous or parent
                match command:
                    case NativeCommand():
                        block_id = add(command.opcode, owner, fields=native_fields(command.fields))
                        blocks[block_id].inputs = native_inputs(command.inputs, block_id)
                        if command.opcode == "control_stop":
                            blocks[block_id].mutation = {"tagName": "mutation", "children": [], "hasnext": "true" if command.fields.get("STOP_OPTION") == "other scripts in sprite" else "false"}
                        for name, body in command.substacks.items():
                            substack(block_id, name, body)
                    case ProcedureCall(proc, values):
                        if id(proc) not in procedures:
                            raise ValueError(f"Undeclared procedure: {proc.name}")
                        if len(values) != len(proc.arguments):
                            raise ValueError(f"Wrong argument count: {proc.name}")
                        block_id = add("procedures_call", owner)
                        blocks[block_id].mutation = procedure_mutation(proc)
                        blocks[block_id].inputs = {f"arg:{i}": value_input(value, block_id) for i, value in enumerate(values)}
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
                        if isinstance(times, (int, float)) and times < 0:
                            raise ValueError("Repeat count must be nonnegative")
                        block_id = add("control_repeat", owner)
                        blocks[block_id].inputs = {"TIMES": numeric(times, block_id)}
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

        for proc in sprite.procedures:
            if len({arg.name for arg in proc.arguments}) != len(proc.arguments):
                raise ValueError("Procedure argument names must be unique")
            hat = add("procedures_definition", None, top_level=True)
            prototype = add("procedures_prototype", hat)
            blocks[prototype].shadow = True
            blocks[prototype].mutation = procedure_mutation(proc, prototype=True)
            blocks[hat].inputs = {"custom_block": [1, prototype]}
            for i, arg in enumerate(proc.arguments):
                node = add("argument_reporter_boolean" if arg.boolean else "argument_reporter_string_number",
                           prototype, fields={"VALUE": [arg.name, None]})
                blocks[node].shadow = True
                blocks[prototype].inputs[f"arg:{i}"] = [1, node]
            active_procedure = proc
            blocks[hat].next = sequence(proc.body, hat)
            active_procedure = None

        for script in sprite.scripts:
            if script.detached:
                sequence(script.body, None)
                continue
            if script.event is not None:
                hat = add(script.event.opcode, None, fields=native_fields(script.event.fields), top_level=True)
                blocks[hat].inputs = native_inputs(script.event.inputs, hat)
            elif script.clicked:
                hat = add("event_whenstageclicked" if is_stage else "event_whenthisspriteclicked", None, top_level=True)
            elif script.message is not None:
                hat = add("event_whenbroadcastreceived", None, fields=message_fields(script.message, "BROADCAST_OPTION"), top_level=True)
            elif script.key is None:
                hat = add("event_whenflagclicked", None, top_level=True)
            else:
                key_value = script.key.value if isinstance(script.key, Key) else script.key
                hat = add("event_whenkeypressed", None, fields={"KEY_OPTION": [key_value, None]}, top_level=True)
            blocks[hat].next = sequence(script.body, hat)
        target: dict[str, Json] = {
            **base, "isStage": False, "name": sprite.name,
            "variables": {v.id or f"var:{v.name}": [v.name, v.initial] for v in sprite.variables},
            "lists": {item.id or f"list:{item.name}": [item.name, list(item.initial)] for item in sprite.lists},
            "blocks": {key: block.json(i) for i, (key, block) in enumerate(blocks.items(), 1)},
            "costumes": [costume(c, c.name or ("Default" if i == 0 else f"Costume {i + 1}")) for i, c in enumerate((sprite.costume, *sprite.costumes))],
            "sounds": [sound(s) for s in sprite.sounds],
            "x": sprite.x, "y": sprite.y, "size": sprite.size, "direction": sprite.direction,
            "visible": sprite.visible, "draggable": sprite.draggable, "rotationStyle": sprite.rotation_style,
            "currentCostume": sprite.current_costume,
            "volume": sprite.volume,
            "layerOrder": sprite.layer_order if sprite.layer_order is not None else len(targets),
        }
        if is_stage:
            target.update(
                tempo=game.tempo, videoTransparency=game.video_transparency,
                videoState=game.video_state, textToSpeechLanguage=game.text_to_speech_language,
            )
            stage = targets[0]
            assert isinstance(stage, dict)
            for key in ("blocks", "costumes", "sounds", "currentCostume", "volume", "lists", "tempo",
                        "videoTransparency", "videoState", "textToSpeechLanguage"):
                if key != "lists" or sprite.lists:
                    stage[key] = target[key]
        else:
            targets.append(target)
    project: dict[str, Json] = {
        "targets": targets, "monitors": list(game.monitors), "extensions": list(game.extensions),
        "meta": game.meta or {"semver": "3.0.0", "vm": "0.2.0", "agent": "itchy"},
    }
    assets["project.json"] = json.dumps(project, allow_nan=False).encode()
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in sorted(assets.items()):
            info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
    return output.getvalue()
