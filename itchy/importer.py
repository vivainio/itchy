"""Translate Scratch project archives into Python itchy project source."""
from __future__ import annotations

import ast
import json
import keyword
from collections import Counter
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from zipfile import BadZipFile, ZipFile

from itchy import game as game_api


_API_NAMES = {name for name in vars(game_api) if not name.startswith("_")}
_BUILTIN_NAMES = set(__builtins__) if isinstance(__builtins__, dict) else set(dir(__builtins__))


BOOLEAN_OPCODES = {
    "operator_equals", "operator_gt", "operator_lt", "operator_and", "operator_or",
    "operator_not", "operator_contains", "data_listcontainsitem", "sensing_mousedown",
    "sensing_keypressed", "sensing_touchingobject", "sensing_touchingcolor",
    "sensing_coloristouchingcolor", "argument_reporter_boolean",
}
MENU_OPCODES = {
    "looks_costume", "looks_backdrops", "sensing_keyoptions", "sensing_of_object_menu",
    "control_create_clone_of_menu", "event_broadcast_menu", "sound_sounds_menu",
    "motion_goto_menu", "motion_pointtowards_menu", "pen_menu_colorParam",
}
HAT_OPCODES = {
    "event_whenflagclicked", "event_whenkeypressed", "event_whenbroadcastreceived",
    "event_whenthisspriteclicked", "event_whenstageclicked", "event_whenbackdropswitchesto",
    "event_whengreaterthan", "control_start_as_clone",
}
LITERAL_OPCODES = {
    "math_number": 4, "math_positive_number": 5, "math_integer": 6,
    "math_whole_number": 7, "math_angle": 8, "colour_picker": 9, "text": 10,
}


def _loads_json(data: bytes, source: Path) -> dict[str, object]:
    try:
        project = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{source} is not a valid Scratch project (.sb3)") from error
    if not isinstance(project, dict) or not isinstance(project.get("targets"), list):
        raise ValueError(f"{source} is not a valid Scratch project (.sb3)")
    return project


def _string(value: object) -> str:
    return value if isinstance(value, str) else str(value)


def _python_name(value: str, fallback: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    words = re.sub(r"[^A-Za-z0-9]+", "_", words).strip("_").lower()
    if not words:
        words = fallback
    if words[0].isdigit() or keyword.iskeyword(words):
        words = f"{fallback}_{words}"
    return words


class PythonImporter:
    def __init__(self, source: Path, project: dict[str, object], archive: ZipFile, assets_dir: Path):
        self.source = source
        self.project = project
        self.archive = archive
        self.assets_dir = assets_dir
        self.targets = [target for target in project["targets"] if isinstance(target, dict)]
        self.stage = next((target for target in self.targets if target.get("isStage")), None)
        if self.stage is None:
            raise ValueError(f"{source} has no Scratch stage")
        self.vars: dict[str, tuple[str, str]] = {}
        self.lists: dict[str, tuple[str, str]] = {}
        self.messages: dict[str, tuple[str, str]] = {}
        self.target_vars: dict[str, dict[str, str]] = {}
        self.target_lists: dict[str, dict[str, str]] = {}
        self.procedures: dict[str, dict[str, dict[str, object]]] = {}
        self.procedure_symbols: dict[tuple[str, str], str] = {}
        self.argument_symbols: dict[tuple[str, str, str], str] = {}
        self.argument_names: dict[tuple[str, str, str], str] = {}
        self.block_symbols: dict[tuple[str, str], dict[str, object]] = {}
        self.visited_blocks: set[tuple[str, str]] = set()
        self.emitted_command_blocks: set[tuple[str, str]] = set()
        self.unresolved_procedures: list[tuple[str, str]] = []
        self.mismatched_procedure_calls: list[tuple[str, str, int, int]] = []
        self.detached_stacks = 0
        self.generic_fallbacks: Counter[str] = Counter()
        self.structural_fallbacks: Counter[str] = Counter()
        self.target_sounds: dict[str, dict[str, str]] = {}
        self.lines: list[str] = []
        self.used_names: set[str] = set()
        self._prepare_declarations()

    def _name(self, value: str, fallback: str, *, prefix: str = "") -> str:
        base = _python_name(value, fallback)
        if prefix:
            base = f"{prefix}_{base}"
        elif base in _API_NAMES or base in _BUILTIN_NAMES:
            base = f"game_{base}"
        name = base
        suffix = 2
        while name in self.used_names:
            name = f"{base}_{suffix}"
            suffix += 1
        self.used_names.add(name)
        return name

    def _prepare_declarations(self) -> None:
        for target_index, target in enumerate(self.targets):
            target_key = _string(target.get("name", f"target_{target_index}"))
            target_vars: dict[str, str] = {}
            target_lists: dict[str, str] = {}
            for item_id, data in target.get("variables", {}).items() if isinstance(target.get("variables"), dict) else ():
                if not isinstance(data, list) or len(data) < 2:
                    continue
                symbol = self._name(_string(data[0]), f"variable_{target_index}")
                self.vars[str(item_id)] = (symbol, target_key)
                target_vars[str(item_id)] = symbol
                value = data[1]
                cls = "NumberVariable" if isinstance(value, (int, float)) and not isinstance(value, bool) else "StringVariable"
                self.lines.append(f"{symbol} = {cls}({_string(data[0])!r}, {value!r}, id={str(item_id)!r})")
            for item_id, data in target.get("lists", {}).items() if isinstance(target.get("lists"), dict) else ():
                if not isinstance(data, list) or len(data) < 2:
                    continue
                symbol = self._name(_string(data[0]), f"list_{target_index}")
                self.lists[str(item_id)] = (symbol, target_key)
                target_lists[str(item_id)] = symbol
                values = tuple(data[1]) if isinstance(data[1], list) else ()
                self.lines.append(f"{symbol} = ScratchList({_string(data[0])!r}, {values!r}, id={str(item_id)!r})")
            self.target_vars[target_key] = target_vars
            self.target_lists[target_key] = target_lists

        broadcasts = self.stage.get("broadcasts", {}) if self.stage else {}
        if isinstance(broadcasts, dict):
            for message_index, (message_id, name) in enumerate(broadcasts.items()):
                symbol = self._name(_string(name), f"message_{message_index}")
                self.messages[str(message_id)] = (symbol, _string(name))
                self.lines.append(f"{symbol} = Message({_string(name)!r}, id={str(message_id)!r})")

        for target_index, target in enumerate(self.targets):
            target_key = _string(target.get("name", f"target_{target_index}"))
            blocks = target.get("blocks", {})
            if not isinstance(blocks, dict):
                continue
            self.block_symbols[(target_key, "blocks")] = blocks
            definitions: list[tuple[str, dict[str, object], dict[str, object]]] = []
            for block_id, block in blocks.items():
                if not isinstance(block, dict) or block.get("opcode") != "procedures_definition":
                    continue
                self.visited_blocks.add((target_key, str(block_id)))
                proto_ref = block.get("inputs", {}).get("custom_block") if isinstance(block.get("inputs"), dict) else None
                proto_id = proto_ref[1] if isinstance(proto_ref, list) and len(proto_ref) > 1 else None
                prototype = blocks.get(proto_id) if isinstance(proto_id, str) else None
                if isinstance(proto_id, str):
                    self.visited_blocks.add((target_key, proto_id))
                mutation = prototype.get("mutation", {}) if isinstance(prototype, dict) else {}
                if not isinstance(mutation, dict):
                    continue
                proccode = _string(mutation.get("proccode", ""))
                ids = self._json_array(mutation.get("argumentids"))
                names = self._json_array(mutation.get("argumentnames"))
                defaults = self._json_array(mutation.get("argumentdefaults"))
                argument_types = [piece == "%b" for piece in re.findall(r"%[bs]", proccode)]
                args: list[str] = []
                for arg_index, arg_id in enumerate(ids):
                    arg_name = _string(names[arg_index]) if arg_index < len(names) else f"arg{arg_index + 1}"
                    arg_symbol = self._name(arg_name, f"argument_{arg_index + 1}")
                    args.append(arg_symbol)
                    self.argument_symbols[(target_key, str(block_id), _string(arg_id))] = arg_symbol
                    self.argument_names[(target_key, str(block_id), arg_name)] = arg_symbol
                    self.lines.append(
                        f"{arg_symbol} = Argument({arg_name!r}, boolean={argument_types[arg_index] if arg_index < len(argument_types) else False!r})"
                    )
                proc_symbol = self._name(_string(proccode), f"procedure_{len(definitions) + 1}", prefix="custom")
                self.procedure_symbols[(target_key, _string(block_id))] = proc_symbol
                procedure = {
                    "symbol": proc_symbol, "block_id": _string(block_id), "prototype_id": _string(proto_id),
                    "proccode": proccode, "argument_ids": ids, "argument_names": names,
                    "argument_defaults": defaults, "arguments": args,
                    "warp": str(mutation.get("warp", "false")).lower() == "true",
                    "body_id": block.get("next"),
                }
                definitions.append((_string(block_id), procedure, prototype if isinstance(prototype, dict) else {}))
            defined_codes = {str(proc["proccode"]) for _, proc, _ in definitions}
            for call in blocks.values():
                if not isinstance(call, dict) or call.get("opcode") != "procedures_call":
                    continue
                mutation = call.get("mutation", {})
                if not isinstance(mutation, dict):
                    continue
                proccode = _string(mutation.get("proccode", ""))
                if proccode in defined_codes:
                    continue
                self.unresolved_procedures.append((target_key, proccode))
                ids = self._json_array(mutation.get("argumentids"))
                argument_types = [piece == "%b" for piece in re.findall(r"%[bs]", proccode)]
                args: list[str] = []
                synthetic_id = f"unresolved_{len(definitions)}"
                for arg_index, arg_id in enumerate(ids):
                    arg_symbol = self._name(f"arg_{arg_index + 1}", f"argument_{arg_index + 1}")
                    args.append(arg_symbol)
                    self.argument_symbols[(target_key, synthetic_id, _string(arg_id))] = arg_symbol
                    bool_type = argument_types[arg_index] if arg_index < len(argument_types) else False
                    self.lines.append(f"{arg_symbol} = Argument('arg{arg_index + 1}', boolean={bool_type!r})")
                procedure = {
                    "symbol": self._name(proccode, f"procedure_{len(definitions) + 1}", prefix="custom"), "block_id": synthetic_id,
                    "prototype_id": "", "proccode": proccode, "argument_ids": ids,
                    "argument_names": [f"arg{i + 1}" for i in range(len(ids))],
                    "argument_defaults": [], "arguments": args, "warp": False, "body_id": None,
                }
                definitions.append((synthetic_id, procedure, {}))
                defined_codes.add(proccode)
            self.procedures[target_key] = {str(proc["proccode"]): proc for _, proc, _ in definitions}
            for _, proc, _ in definitions:
                arg_tuple = "(" + ", ".join(proc["arguments"]) + ("," if len(proc["arguments"]) == 1 else "") + ")"
                self.lines.append(
                    f"{proc['symbol']} = Procedure({proc['proccode']!r}, {arg_tuple}, warp={proc['warp']!r}, "
                    f"proccode={proc['proccode']!r}, argument_ids={tuple(proc['argument_ids'])!r}, "
                    f"argument_defaults={tuple(proc['argument_defaults'])!r})"
                )
            for _, proc, _ in definitions:
                if proc["body_id"]:
                    body = self._chain(
                        target_key, _string(proc["body_id"]), active_proc=_string(proc["block_id"])
                    )
                    self.lines.append(f"{proc['symbol']}.body = {body}")

    @staticmethod
    def _json_array(value: object) -> list[object]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return value if isinstance(value, list) else []

    def _target_symbol(self, target_key: str, item_id: str, *, kind: str) -> str:
        primary = self.target_vars if kind == "variable" else self.target_lists
        global_target = _string(self.stage.get("name", "Stage")) if self.stage else "Stage"
        if item_id in primary.get(target_key, {}):
            return primary[target_key][item_id]
        if item_id in primary.get(global_target, {}):
            return primary[global_target][item_id]
        entries = self.vars if kind == "variable" else self.lists
        if item_id in entries:
            return entries[item_id][0]
        raise ValueError(f"Unknown Scratch {kind} id {item_id!r} in {target_key}")

    def _field(self, target_key: str, field_name: str, value: object) -> str:
        if not isinstance(value, list) or not value:
            return repr(value)
        name = _string(value[0])
        item_id = _string(value[1]) if len(value) > 1 and value[1] is not None else ""
        if field_name == "VARIABLE" and item_id:
            return self._target_symbol(target_key, item_id, kind="variable")
        if field_name == "LIST" and item_id:
            return self._target_symbol(target_key, item_id, kind="list")
        return repr(name)

    def _menu(self, target_key: str, block: dict[str, object]) -> str:
        fields = block.get("fields", {})
        if not isinstance(fields, dict) or not fields:
            return "Menu('unknown', 'unknown', '')"
        field_name, value = next(iter(fields.items()))
        field_value = value[0] if isinstance(value, list) and value else value
        field_id = value[1] if isinstance(value, list) and len(value) > 1 else None
        if block.get("opcode") == "event_broadcast_menu" and field_id is not None:
            message = self.messages.get(_string(field_id))
            if message is not None:
                return message[0]
        return f"Menu({_string(block.get('opcode'))!r}, {str(field_name)!r}, {_string(field_value)!r}, id={field_id!r})"

    def _literal(self, target_key: str, literal: object) -> str:
        if not isinstance(literal, list) or not literal:
            return repr(literal)
        type_code = literal[0]
        if not isinstance(type_code, int):
            return repr(literal)
        value = literal[1] if len(literal) > 1 else ""
        if type_code in (12, 13) and len(literal) > 2:
            return f"ScratchLiteral({type_code!r}, {_string(value)!r}, id={_string(literal[2])!r})"
        if type_code == 11 and len(literal) > 2:
            return f"ScratchLiteral(11, {_string(value)!r}, id={_string(literal[2])!r})"
        return f"ScratchLiteral({type_code!r}, {_string(value)!r})"

    def _input(self, target_key: str, name: str, data: object, active_proc: str | None) -> str:
        if not isinstance(data, list) or len(data) < 2:
            return repr(data)
        payload = data[1]
        if isinstance(payload, list) and payload and isinstance(payload[0], int):
            if name == "BROADCAST_INPUT" and payload[0] == 11 and len(payload) > 2:
                message = self.messages.get(_string(payload[2]))
                if message is not None:
                    return message[0]
            return self._literal(target_key, payload)
        if isinstance(payload, str):
            blocks = self.block_symbols[(target_key, "blocks")]
            child = blocks.get(payload)
            if isinstance(child, dict):
                if child.get("shadow") and self._is_menu(child):
                    return self._menu(target_key, child)
                return self._expression(target_key, payload, active_proc)
        if len(data) > 2 and isinstance(data[2], list):
            return self._literal(target_key, data[2])
        return repr(payload)

    @staticmethod
    def _is_menu(block: dict[str, object]) -> bool:
        opcode = _string(block.get("opcode"))
        return opcode in MENU_OPCODES or opcode.endswith("_menu") or opcode.endswith("_options")

    def _expression(self, target_key: str, block_id: str, active_proc: str | None = None,
                    *, as_command: bool = False) -> str:
        self.visited_blocks.add((target_key, block_id))
        blocks = self.block_symbols[(target_key, "blocks")]
        block = blocks.get(block_id)
        if not isinstance(block, dict):
            raise ValueError(f"Missing Scratch block {block_id!r} in {target_key}")
        opcode = _string(block.get("opcode"))
        fields = block.get("fields", {}) if isinstance(block.get("fields"), dict) else {}
        inputs = block.get("inputs", {}) if isinstance(block.get("inputs"), dict) else {}
        if opcode in LITERAL_OPCODES:
            field_name = next(iter(fields), "")
            value = fields.get(field_name, "")
            value = value[0] if isinstance(value, list) and value else value
            return f"ScratchLiteral({LITERAL_OPCODES[opcode]!r}, {_string(value)!r})"
        if not as_command and opcode in ("data_variable", "data_listcontents"):
            field_name = "VARIABLE" if opcode == "data_variable" else "LIST"
            field_data = fields.get(field_name)
            if isinstance(field_data, list) and len(field_data) > 1 and field_data[1] is not None:
                return self._target_symbol(target_key, _string(field_data[1]), kind="variable" if opcode == "data_variable" else "list")
        if opcode.startswith("argument_reporter_") and not as_command:
            field_value = fields.get("VALUE", [""])
            argument_id = _string(field_value[1]) if isinstance(field_value, list) and len(field_value) > 1 else ""
            if active_proc is not None:
                symbol = self.argument_symbols.get((target_key, active_proc, argument_id))
                if symbol is None and isinstance(field_value, list) and field_value:
                    symbol = self.argument_names.get((target_key, active_proc, _string(field_value[0])))
                if symbol:
                    return symbol
            name = _string(field_value[0]) if isinstance(field_value, list) and field_value else "argument"
            return f"Argument({name!r}, boolean={opcode.endswith('boolean')!r}, imported=True)"
        if opcode == "procedures_call":
            mutation = block.get("mutation", {})
            proccode = _string(mutation.get("proccode", "")) if isinstance(mutation, dict) else ""
            proc = self.procedures.get(target_key, {}).get(proccode)
            if proc is None:
                raise ValueError(f"Call to unknown Scratch custom block {proccode!r} in {target_key}")
            call_ids = self._json_array(mutation.get("argumentids")) if isinstance(mutation, dict) else []
            definition_ids = [str(arg_id) for arg_id in proc["argument_ids"]]
            if len(call_ids) != len(definition_ids):
                self.mismatched_procedure_calls.append((target_key, proccode, len(call_ids), len(definition_ids)))
            values = []
            for arg_index, arg_id in enumerate(definition_ids):
                input_id = arg_id if arg_id in inputs else str(call_ids[arg_index]) if arg_index < len(call_ids) else arg_id
                input_data = inputs.get(input_id)
                if input_data is not None:
                    values.append(self._input(target_key, input_id, input_data, active_proc))
                else:
                    defaults = proc["argument_defaults"]
                    default = defaults[arg_index] if arg_index < len(defaults) else ""
                    values.append(f"ScratchLiteral({10 if not isinstance(default, bool) else 1}, {_string(default)!r})")
            return f"{proc['symbol']}({', '.join(values)})"

        python_fields = {
            str(field_name): self._field(target_key, str(field_name), value)
            for field_name, value in fields.items()
        }
        normal_inputs: dict[str, str] = {}
        substacks: dict[str, str] = {}
        for input_name, input_data in inputs.items():
            if str(input_name).startswith("SUBSTACK"):
                ref = input_data[1] if isinstance(input_data, list) and len(input_data) > 1 else None
                body = self._chain(target_key, ref, block_id, active_proc) if isinstance(ref, str) else "()"
                substacks[str(input_name)] = body
            else:
                normal_inputs[str(input_name)] = self._input(target_key, str(input_name), input_data, active_proc)
        malformed_position = as_command and self._is_noncommand({"opcode": opcode})
        semantic = self._semantic_block(opcode, normal_inputs, python_fields, substacks, target_key, as_command=as_command)
        if semantic is not None:
            return semantic
        if malformed_position:
            self.structural_fallbacks[opcode] += 1
        else:
            self.generic_fallbacks[opcode] += 1
        args = [repr(opcode)]
        if normal_inputs:
            args.append("inputs={" + ", ".join(f"{key!r}: {value}" for key, value in normal_inputs.items()) + "}")
        if python_fields:
            args.append("fields={" + ", ".join(f"{key!r}: {value}" for key, value in python_fields.items()) + "}")
        if substacks:
            args.append("substacks={" + ", ".join(f"{key!r}: {value}" for key, value in substacks.items()) + "}")
        builder = "block" if as_command else "predicate" if opcode in BOOLEAN_OPCODES else "reporter" if self._value_block(opcode) else "block"
        return f"{builder}({', '.join(args)})"

    def _semantic_block(self, opcode: str, inputs: dict[str, str], fields: dict[str, str],
                        substacks: dict[str, str], target_key: str, *, as_command: bool) -> str | None:
        def inp(name: str, default: str = "0") -> str:
            return inputs.get(name, default)

        def field(name: str, default: str = "") -> str:
            return fields.get(name, repr(default))

        if as_command and self._is_noncommand({"opcode": opcode}):
            return None

        if opcode in {"operator_add", "operator_subtract", "operator_multiply", "operator_divide"}:
            operator = {"operator_add": "+", "operator_subtract": "-", "operator_multiply": "*", "operator_divide": "/"}[opcode]
            return f"({inp('NUM1')} {operator} {inp('NUM2')})"
        if opcode == "operator_equals":
            return f"{inp('OPERAND1')}.equals({inp('OPERAND2')})"
        if opcode in {"operator_gt", "operator_lt"}:
            operator = ">" if opcode == "operator_gt" else "<"
            return f"({inp('OPERAND1')} {operator} {inp('OPERAND2')})"
        if opcode in {"operator_and", "operator_or"}:
            operator = "&" if opcode == "operator_and" else "|"
            return f"({inp('OPERAND1')} {operator} {inp('OPERAND2')})"
        if opcode == "operator_not":
            return f"(~{inp('OPERAND')})"
        if opcode == "operator_random":
            return f"random_number({inp('FROM')}, {inp('TO')})"
        if opcode == "operator_round":
            return f"round_number({inp('NUM')})"
        if opcode == "operator_mathop":
            return f"math_op({field('OPERATOR')}, {inp('NUM')})"
        if opcode == "operator_mod":
            return f"modulo({inp('NUM1')}, {inp('NUM2')})"
        if opcode == "operator_join":
            return f"join({inp('STRING1')}, {inp('STRING2')})"
        if opcode == "operator_length":
            return f"length({inp('STRING')})"
        if opcode == "operator_letter_of":
            return f"letter({inp('LETTER')}, {inp('STRING')})"
        if opcode == "operator_contains":
            return f"contains({inp('STRING1')}, {inp('STRING2')})"

        list_name = field("LIST")
        if opcode == "data_setvariableto":
            return f"{field('VARIABLE')}.set({inp('VALUE')})"
        if opcode == "data_changevariableby":
            return f"{field('VARIABLE')}.add({inp('VALUE')})"
        if opcode == "data_showvariable":
            return f"{field('VARIABLE')}.show()"
        if opcode == "data_hidevariable":
            return f"{field('VARIABLE')}.hide()"
        if opcode == "data_showlist":
            return f"{list_name}.show()"
        if opcode == "data_hidelist":
            return f"{list_name}.hide()"
        list_methods = {
            "data_addtolist": ("append", ("ITEM",)),
            "data_deleteoflist": ("delete", ("INDEX",)),
            "data_deletealloflist": ("clear", ()),
            "data_insertatlist": ("insert", ("INDEX", "ITEM")),
            "data_replaceitemoflist": ("replace", ("INDEX", "ITEM")),
            "data_itemoflist": ("item", ("INDEX",)),
            "data_lengthoflist": ("length", ()),
            "data_itemnumoflist": ("index", ("ITEM",)),
            "data_listcontainsitem": ("contains", ("ITEM",)),
        }
        if opcode in list_methods:
            method, keys = list_methods[opcode]
            args = ", ".join(inp(key) for key in keys)
            return f"{list_name}.{method}({args})"

        if opcode == "control_if":
            return f"if_then({inp('CONDITION')}, *{substacks.get('SUBSTACK', '()')})"
        if opcode == "control_if_else":
            return (f"if_else({inp('CONDITION')}, then={substacks.get('SUBSTACK', '()')}, "
                    f"otherwise={substacks.get('SUBSTACK2', '()')})")
        if opcode == "control_repeat":
            return f"repeat({inp('TIMES')}, *{substacks.get('SUBSTACK', '()')})"
        if opcode == "control_repeat_until":
            return f"repeat_until({inp('CONDITION')}, *{substacks.get('SUBSTACK', '()')})"
        if opcode == "control_forever":
            return f"forever(*{substacks.get('SUBSTACK', '()')})"
        if opcode == "control_while":
            return f"repeat_until(~{inp('CONDITION')}, *{substacks.get('SUBSTACK', '()')})"
        if opcode == "control_wait":
            return f"wait({inp('DURATION')})"
        if opcode == "control_wait_until":
            return f"wait_until({inp('CONDITION')})"
        if opcode == "control_stop":
            return f"stop({field('STOP_OPTION')})"
        if opcode == "control_create_clone_of":
            return f"clone({inp('CLONE_OPTION')})"
        if opcode == "control_delete_this_clone":
            return "delete_clone()"

        motion = {
            "motion_movesteps": f"move({inp('STEPS')})",
            "motion_turnright": f"turn({inp('DEGREES')})",
            "motion_turnleft": f"turn_left({inp('DEGREES')})",
            "motion_pointindirection": f"point_direction({inp('DIRECTION')})",
            "motion_pointtowards": f"point_towards({inp('TOWARDS')})",
            "motion_gotoxy": f"go_to({inp('X')}, {inp('Y')})",
            "motion_goto": f"go_to_target({inp('TO')})",
            "motion_changexby": f"move_x({inp('DX')})",
            "motion_changeyby": f"move_y({inp('DY')})",
            "motion_setx": f"set_x({inp('X')})",
            "motion_sety": f"set_y({inp('Y')})",
            "motion_ifonedgebounce": "bounce()",
            "motion_xposition": "x_position()",
            "motion_yposition": "y_position()",
            "motion_direction": "direction()",
        }
        if opcode in motion:
            return motion[opcode]
        if opcode in {"looks_show", "looks_hide", "looks_nextcostume", "looks_cleargraphiceffects"}:
            return {"looks_show": "show()", "looks_hide": "hide()", "looks_nextcostume": "next_costume()",
                    "looks_cleargraphiceffects": "clear_effects()"}[opcode]
        if opcode == "looks_setsizeto":
            return f"set_size({inp('SIZE')})"
        if opcode == "looks_changesizeby":
            return f"change_size({inp('CHANGE')})"
        if opcode == "looks_say":
            return f"say({inp('MESSAGE')})"
        if opcode == "looks_sayforsecs":
            return f"say({inp('MESSAGE')}, {inp('SECS')})"
        if opcode == "looks_think":
            return f"think({inp('MESSAGE')})"
        if opcode == "looks_thinkforsecs":
            return f"think({inp('MESSAGE')}, {inp('SECS')})"
        if opcode == "looks_switchcostumeto":
            return f"switch_costume({inp('COSTUME')})"
        if opcode == "looks_seteffectto":
            return f"set_effect({field('EFFECT')}, {inp('VALUE')})"
        if opcode == "looks_changeeffectby":
            return f"change_effect({field('EFFECT')}, {inp('CHANGE')})"
        if opcode == "looks_size":
            return "reporter('looks_size')"
        if opcode == "looks_costumenumbername":
            return f"costume_number_or_name({field('NUMBER_NAME')})"
        if opcode == "looks_switchbackdropto":
            return f"switch_backdrop({inp('BACKDROP')})"
        if opcode == "motion_setrotationstyle":
            return f"rotation_style({field('STYLE')})"

        if opcode == "event_broadcast":
            return f"broadcast({inp('BROADCAST_INPUT')})"
        if opcode == "event_broadcastandwait":
            return f"broadcast({inp('BROADCAST_INPUT')}, wait=True)"
        if opcode == "sound_play":
            menu = inputs.get("SOUND_MENU", "")
            sound_name = None
            match = re.search(r"Menu\([^,]+, [^,]+, (.+?), id=", menu)
            if match:
                sound_name = _string(ast.literal_eval(match.group(1)))
            symbol = self.target_sounds.get(target_key, {}).get(sound_name or "")
            if symbol:
                return f"play_sound({symbol})"
            return f"play_sound({menu})"
        if opcode == "sound_playuntildone":
            menu = inputs.get("SOUND_MENU", "")
            sound_name = None
            match = re.search(r"Menu\([^,]+, [^,]+, (.+?), id=", menu)
            if match:
                sound_name = _string(ast.literal_eval(match.group(1)))
            symbol = self.target_sounds.get(target_key, {}).get(sound_name or "")
            if symbol:
                return f"play_sound({symbol}, wait=True)"
            return f"play_sound({menu}, wait=True)"
        if opcode == "sound_stopallsounds":
            return "stop_sounds()"
        if opcode == "sound_setvolumeto":
            return f"set_volume({inp('VOLUME')})"
        if opcode == "sound_changevolumeby":
            return f"change_volume({inp('VOLUME')})"

        if opcode == "sensing_mousedown":
            return "mouse_down()"
        if opcode == "sensing_mousex":
            return "mouse_x()"
        if opcode == "sensing_mousey":
            return "mouse_y()"
        if opcode == "sensing_timer":
            return "timer()"
        if opcode == "sensing_resettimer":
            return "reset_timer()"
        if opcode == "sensing_answer":
            return "answer()"
        if opcode == "sensing_keypressed":
            return f"key_down({inp('KEY_OPTION')}.value)"
        if opcode == "sensing_askandwait":
            return f"ask({inp('QUESTION')})"
        if opcode == "sensing_touchingobject":
            return f"touching({inp('TOUCHINGOBJECTMENU')}.value)"
        if opcode == "sensing_of":
            return f"property_of({inp('OBJECT')}, {field('PROPERTY')})"
        if opcode == "sensing_setdragmode":
            return f"set_drag_mode({field('DRAG_MODE')})"

        if opcode == "pen_stamp":
            return "stamp()"
        if opcode == "pen_penUp":
            return "pen_up()"
        if opcode == "pen_penDown":
            return "pen_down()"
        if opcode == "pen_clear":
            return "clear_pen()"
        if opcode == "pen_setPenSizeTo":
            return f"set_pen_size({inp('SIZE')})"
        if opcode == "pen_setPenColorToColor":
            return f"set_pen_color({inp('COLOR')})"
        if opcode == "pen_setPenColorParamTo":
            return f"set_pen_color_param({field('COLOR_PARAM')}, {inp('VALUE')})"
        return None

    @staticmethod
    def _value_block(opcode: str) -> bool:
        return opcode.startswith(("operator_", "sensing_", "motion_", "looks_", "sound_", "data_", "argument_reporter_"))

    def _chain(self, target_key: str, first_id: object, parent_id: str | None = None,
               active_proc: str | None = None) -> str:
        if not isinstance(first_id, str):
            return "()"
        blocks = self.block_symbols[(target_key, "blocks")]
        commands: list[str] = []
        seen: set[str] = set()
        current: str | None = first_id
        while current and current not in seen:
            if (target_key, current) in self.emitted_command_blocks:
                break
            seen.add(current)
            self.emitted_command_blocks.add((target_key, current))
            self.visited_blocks.add((target_key, current))
            block = blocks.get(current)
            if not isinstance(block, dict):
                break
            opcode = _string(block.get("opcode"))
            if opcode in ("procedures_definition", "procedures_prototype"):
                break
            commands.append(self._expression(target_key, current, active_proc, as_command=True))
            nxt = block.get("next")
            current = nxt if isinstance(nxt, str) else None
        return "(" + ", ".join(commands) + ("," if len(commands) == 1 else "") + ")"

    def emit(self) -> str:
        self.lines[:0] = [
            '"""Python reconstruction of the imported Scratch project."""',
            "from pathlib import Path",
            "from itchy.game import *",
            "",
            "_root = Path(__file__).parent",
            "",
        ]
        sprite_symbols: list[str] = []
        stage_symbol = "_stage"
        stage_name = _string(self.stage.get("name", "Stage")) if self.stage else "Stage"
        for target_index, target in enumerate(self.targets):
            target_key = _string(target.get("name", f"target_{target_index}"))
            is_stage = bool(target.get("isStage"))
            symbol = stage_symbol if is_stage else self._name(_string(target.get("name", "")), f"sprite_{target_index}")
            if not is_stage:
                sprite_symbols.append(symbol)
            blocks = target.get("blocks", {})
            if not isinstance(blocks, dict):
                blocks = {}
            costume_symbols = self._costumes(target, target_index)
            sound_symbols = self._sounds(target, target_index)
            scripts: list[str] = []
            for block_id, block in blocks.items():
                if not isinstance(block, dict) or not block.get("topLevel"):
                    continue
                self.visited_blocks.add((target_key, str(block_id)))
                opcode = _string(block.get("opcode"))
                if opcode == "procedures_definition":
                    continue
                if opcode not in HAT_OPCODES and self._is_noncommand(block):
                    continue
                body = self._chain(target_key, block.get("next"), str(block_id))
                if opcode == "event_whenflagclicked":
                    scripts.append(f"on_start(*{body})")
                elif opcode == "control_start_as_clone":
                    scripts.append(f"on_clone(*{body})")
                elif opcode == "event_whenkeypressed":
                    key_field = block.get("fields", {}).get("KEY_OPTION", [""]) if isinstance(block.get("fields"), dict) else [""]
                    key_value = key_field[0] if isinstance(key_field, list) and key_field else ""
                    scripts.append(f"on_key({_string(key_value)!r}, *{body})")
                elif opcode in ("event_whenthisspriteclicked", "event_whenstageclicked"):
                    scripts.append(f"on_click(*{body})")
                elif opcode == "event_whenbroadcastreceived":
                    field = block.get("fields", {}).get("BROADCAST_OPTION", [""]) if isinstance(block.get("fields"), dict) else [""]
                    message_id = _string(field[1]) if isinstance(field, list) and len(field) > 1 else ""
                    message = self.messages.get(message_id)
                    if message is None:
                        message_name = _string(field[0]) if isinstance(field, list) and field else ""
                        message_symbol = f"Message({message_name!r})"
                    else:
                        message_symbol = message[0]
                    scripts.append(f"on_message({message_symbol}, *{body})")
                elif opcode not in HAT_OPCODES:
                    detached = self._chain(target_key, str(block_id))
                    scripts.append(f"Script(None, {detached}, detached=True)")
                    self.detached_stacks += 1
                else:
                    event_fields = block.get("fields", {}) if isinstance(block.get("fields"), dict) else {}
                    fields = {str(key): self._field(target_key, str(key), value) for key, value in event_fields.items()}
                    field_src = "fields={" + ", ".join(f"{key!r}: {value}" for key, value in fields.items()) + "}" if fields else ""
                    event_expr = f"block({opcode!r}{', ' if field_src else ''}{field_src})"
                    self.generic_fallbacks[opcode] += 1
                    scripts.append(f"on_event({event_expr}, *{body})")
            scripts.extend(self._detached_stacks(target_key, blocks))
            self.lines.append(f"{symbol} = Sprite(")
            self.lines.append(f"    {_string(target.get('name', 'Stage'))!r},")
            if costume_symbols:
                self.lines.append(f"    {costume_symbols[0]},")
                self.lines.append("    (")
                for script in scripts:
                    self.lines.append(f"        {script},")
                self.lines.append("    ),")
            else:
                self.lines.append("    Costume('<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1\" height=\"1\"/>'),")
                self.lines.append("    (),")
            self.lines.append(f"    x={target.get('x', 0)!r}, y={target.get('y', 0)!r},")
            self.lines.append(f"    sounds={self._tuple_expr(sound_symbols)},")
            self.lines.append(f"    costumes={self._tuple_expr(costume_symbols[1:])},")
            self.lines.append(f"    procedures={self._tuple_expr(tuple(proc['symbol'] for proc in self.procedures.get(target_key, {}).values()))},")
            variables = () if is_stage else tuple(self.target_vars.get(target_key, {}).values())
            lists = () if is_stage else tuple(self.target_lists.get(target_key, {}).values())
            self.lines.append(f"    variables={self._tuple_expr(variables)},")
            self.lines.append(f"    lists={self._tuple_expr(lists)},")
            self.lines.append(f"    size={target.get('size', 100)!r}, direction={target.get('direction', 90)!r},")
            self.lines.append(f"    visible={target.get('visible', True)!r}, current_costume={target.get('currentCostume', 0)!r},")
            self.lines.append(f"    rotation_style={_string(target.get('rotationStyle', 'all around'))!r},")
            self.lines.append(f"    draggable={target.get('draggable', False)!r}, layer_order={target.get('layerOrder')!r}, volume={target.get('volume', 100)!r},")
            self.lines.append(")")
            self.lines.append("")

        global_vars = tuple(self.target_vars.get(stage_name, {}).values())
        global_lists = tuple(self.target_lists.get(stage_name, {}).values())
        messages = tuple(symbol for symbol, _ in self.messages.values())
        sprites = tuple(sprite_symbols)
        stage = stage_symbol if self.stage else "None"
        extensions = tuple(self.project.get("extensions", []))
        self.lines.append("game = Game(")
        self.lines.append(f"    {_string(self.source.stem)!r}, variables={self._tuple_expr(global_vars)}, sprites={self._tuple_expr(sprites)},")
        self.lines.append(f"    messages={self._tuple_expr(messages)}, lists={self._tuple_expr(global_lists)}, extensions={extensions!r}, stage={stage},")
        self.lines.append(f"    monitors={tuple(self.project.get('monitors', []))!r}, meta={self.project.get('meta', {})!r},")
        if self.stage:
            self.lines.append(f"    tempo={self.stage.get('tempo', 60)!r}, video_transparency={self.stage.get('videoTransparency', 50)!r},")
            self.lines.append(f"    video_state={_string(self.stage.get('videoState', 'on'))!r}, text_to_speech_language={self.stage.get('textToSpeechLanguage')!r},")
        self.lines.append(")")
        return "\n".join(self.lines) + "\n"

    def _detached_stacks(self, target_key: str, blocks: dict[str, object]) -> list[str]:
        incoming: set[str] = set()
        for block_id, block in blocks.items():
            if not isinstance(block, dict):
                continue
            nxt = block.get("next")
            if isinstance(nxt, str):
                incoming.add(nxt)
            inputs = block.get("inputs", {})
            if isinstance(inputs, dict):
                for data in inputs.values():
                    if isinstance(data, list):
                        for item in data[1:]:
                            if isinstance(item, str) and item in blocks:
                                incoming.add(item)
                            elif isinstance(item, list) and item and isinstance(item[0], str) and item[0] in blocks:
                                incoming.add(item[0])
        roots: list[str] = []
        for block_id, block in blocks.items():
            if not isinstance(block, dict) or (target_key, str(block_id)) in self.visited_blocks:
                continue
            opcode = _string(block.get("opcode"))
            if self._is_noncommand(block) or str(block_id) in incoming:
                continue
            roots.append(str(block_id))
        scripts: list[str] = []
        for block_id in roots:
            if (target_key, block_id) in self.visited_blocks:
                continue
            body = self._chain(target_key, block_id)
            if body != "()":
                scripts.append(f"Script(None, {body}, detached=True)")
                self.detached_stacks += 1
        return scripts

    def _is_noncommand(self, block: dict[str, object]) -> bool:
        opcode = _string(block.get("opcode"))
        if opcode in BOOLEAN_OPCODES or self._is_menu(block):
            return True
        if opcode in LITERAL_OPCODES or opcode.startswith("argument_reporter_"):
            return True
        if opcode in ("data_variable", "data_listcontents", "data_itemoflist", "data_lengthoflist", "data_itemnumoflist"):
            return True
        if opcode.startswith("operator_"):
            return True
        if opcode in ("motion_xposition", "motion_yposition", "motion_direction", "looks_costumenumbername", "looks_size",
                      "sensing_answer", "sensing_mousex", "sensing_mousey", "sensing_timer", "sensing_of", "sound_volume"):
            return True
        return opcode in ("procedures_definition", "procedures_prototype")

    @staticmethod
    def _tuple_expr(symbols: tuple[str, ...]) -> str:
        return "(" + ", ".join(symbols) + ("," if len(symbols) == 1 else "") + ")"

    def _costumes(self, target: dict[str, object], target_index: int) -> tuple[str, ...]:
        result: list[str] = []
        for costume_index, costume in enumerate(target.get("costumes", [])):
            if not isinstance(costume, dict):
                continue
            path = self._asset(costume)
            symbol = f"_c_{target_index}_{costume_index}"
            self.lines.append(
                f"{symbol} = Costume(_root / 'assets' / {path!r}, "
                f"{costume.get('rotationCenterX', 0)!r}, {costume.get('rotationCenterY', 0)!r}, "
                f"name={_string(costume.get('name', ''))!r}, bitmap_resolution={costume.get('bitmapResolution', 1)!r})"
            )
            result.append(symbol)
        return tuple(result)

    def _sounds(self, target: dict[str, object], target_index: int) -> tuple[str, ...]:
        result: list[str] = []
        for sound_index, sound in enumerate(target.get("sounds", [])):
            if not isinstance(sound, dict):
                continue
            path = self._asset(sound)
            symbol = f"_s_{target_index}_{sound_index}"
            self.lines.append(
                f"{symbol} = Sound({_string(sound.get('name', 'Sound'))!r}, _root / 'assets' / {path!r}, "
                f"rate={sound.get('rate', 0)!r}, sample_count={sound.get('sampleCount', 0)!r}, "
                f"format={_string(sound.get('format', ''))!r})"
            )
            self.target_sounds.setdefault(_string(target.get("name", f"target_{target_index}")), {})[
                _string(sound.get("name", "Sound"))
            ] = symbol
            result.append(symbol)
        return tuple(result)

    def _asset(self, descriptor: dict[str, object]) -> str:
        asset_name = _string(descriptor.get("md5ext", ""))
        safe_name = PurePosixPath(asset_name).name
        if not safe_name or safe_name != asset_name:
            raise ValueError(f"Unsafe asset path in {self.source}: {asset_name!r}")
        try:
            data = self.archive.read(asset_name)
        except KeyError as error:
            raise ValueError(f"Missing Scratch asset {asset_name!r} in {self.source}") from error
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        destination = self.assets_dir / safe_name
        if not destination.exists():
            destination.write_bytes(data)
        return safe_name


def import_project(source: Path, directory: Path) -> None:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Scratch project not found: {source}")
    if source.suffix.lower() != ".sb3":
        raise ValueError(f"Expected a Scratch .sb3 file: {source}")
    directory = directory.expanduser().resolve()
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"{directory} must be an empty directory; no files were changed")
    try:
        with ZipFile(source) as archive:
            project = _loads_json(archive.read("project.json"), source)
            directory.mkdir(parents=True, exist_ok=True)
            importer = PythonImporter(source, project, archive, directory / "assets")
            source_code = importer.emit()
    except (BadZipFile, KeyError) as error:
        raise ValueError(f"{source} is not a valid Scratch project (.sb3)") from error
    game_file = directory / "game.py"
    game_file.write_text(source_code)
    formatter = shutil.which("ruff")
    if formatter is not None:
        subprocess.run([formatter, "format", str(game_file)], check=True, capture_output=True, text=True)
    (directory / "itchy.toml").write_text('[project]\nentry = "game.py"\noutput = "dist"\n')
    (directory / "pyproject.toml").write_text(
        '[project]\nname = "imported-scratch-game"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\ndependencies = ["itchy>=0.1.0"]\n'
    )
    (directory / ".gitignore").write_text("dist/\n.venv/\n__pycache__/\n")
    (directory / "README.md").write_text(
        f"# {source.stem}\n\n"
        "This game was translated from Scratch into Python using itchy's native block builders. "
        "Scripts, custom blocks, variables, lists, costumes, and sounds are defined in `game.py` and `assets/`.\n"
    )
    notes = [
        f"# Import notes for {source.name}",
        "",
        "The importer retained disconnected command stacks as detached Python scripts so their blocks remain editable.",
        f"Detached stacks retained: {importer.detached_stacks}.",
        "",
    ]
    if importer.unresolved_procedures:
        notes.extend([
            f"The source contains {len(importer.unresolved_procedures)} custom block call(s) with no definition. "
            "The generated Python includes empty procedure stubs so the calls remain represented.",
            "",
        ])
        notes.extend(f"- `{target}: {proccode}`" for target, proccode in importer.unresolved_procedures)
        notes.append("")
    else:
        notes.extend(["No unresolved custom block calls were found.", ""])
    if importer.mismatched_procedure_calls:
        notes.extend([
            f"The source has {len(importer.mismatched_procedure_calls)} custom block call(s) whose argument count "
            "does not match the procedure definition. Calls were normalized to the defined arguments.",
            "",
        ])
        notes.extend(
            f"- `{target}: {proccode}` — call has {call_count} argument(s), definition has {definition_count}"
            for target, proccode, call_count, definition_count in importer.mismatched_procedure_calls
        )
        notes.append("")
    if importer.generic_fallbacks:
        notes.extend([
            "## Missing dedicated Python builders",
            "",
            "These source opcodes still use the generic native-block fallback. Their block data is retained, "
            "but they do not yet have a purpose-built, idiomatic itchy builder:",
            "",
        ])
        notes.extend(f"- `{opcode}`: {count}" for opcode, count in importer.generic_fallbacks.most_common())
        notes.append("")
    else:
        notes.extend(["All well-formed encountered opcodes were translated to dedicated itchy builders.", ""])
    if importer.structural_fallbacks:
        notes.extend([
            "## Malformed block placements",
            "",
            "These reporter/menu blocks appeared in command-stack positions in the source. Their original block "
            "form is retained because translating them as value expressions would change the graph:",
            "",
        ])
        notes.extend(f"- `{opcode}`: {count}" for opcode, count in importer.structural_fallbacks.most_common())
        notes.append("")
    (directory / "IMPORT_NOTES.md").write_text("\n".join(notes))
    print(f"Imported {source.name} into {directory}\nPython source: {directory / 'game.py'}")
