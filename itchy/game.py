from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
import inspect
import re
from pathlib import Path
from typing import Literal, assert_never


class Key(StrEnum):
    LEFT = "left arrow"
    RIGHT = "right arrow"
    UP = "up arrow"
    DOWN = "down arrow"
    SPACE = "space"
    ENTER = "enter"
    ANY = "any"
    A = "a"
    D = "d"
    W = "w"
    S = "s"


class Condition:
    def equals(self, other: Value) -> Condition:
        return predicate("operator_equals", inputs={"OPERAND1": self, "OPERAND2": other})

    def __add__(self, other: Number) -> NumberExpression:
        return Arithmetic("add", self, other)

    def __radd__(self, other: Number) -> NumberExpression:
        return Arithmetic("add", other, self)

    def __sub__(self, other: Number) -> NumberExpression:
        return Arithmetic("subtract", self, other)

    def __rsub__(self, other: Number) -> NumberExpression:
        return Arithmetic("subtract", other, self)

    def __mul__(self, other: Number) -> NumberExpression:
        return Arithmetic("multiply", self, other)

    def __rmul__(self, other: Number) -> NumberExpression:
        return Arithmetic("multiply", other, self)

    def __truediv__(self, other: Number) -> NumberExpression:
        return Arithmetic("divide", self, other)

    def __rtruediv__(self, other: Number) -> NumberExpression:
        return Arithmetic("divide", other, self)

    def __and__(self, other: Condition) -> Condition:
        return Logic("and", self, other)

    def __or__(self, other: Condition) -> Condition:
        return Logic("or", self, other)

    def __invert__(self) -> Condition:
        return Not(self)

    def __bool__(self) -> bool:
        raise TypeError("Game conditions need if_ builders and &/|/~; Python if/and/or runs at build time")


class NumberExpression:
    def __add__(self, other: Number) -> NumberExpression:
        return Arithmetic("add", self, other)

    def __radd__(self, other: Number) -> NumberExpression:
        return Arithmetic("add", other, self)

    def __sub__(self, other: Number) -> NumberExpression:
        return Arithmetic("subtract", self, other)

    def __rsub__(self, other: Number) -> NumberExpression:
        return Arithmetic("subtract", other, self)

    def __mul__(self, other: Number) -> NumberExpression:
        return Arithmetic("multiply", self, other)

    def __rmul__(self, other: Number) -> NumberExpression:
        return Arithmetic("multiply", other, self)

    def __truediv__(self, other: Number) -> NumberExpression:
        return Arithmetic("divide", self, other)

    def __rtruediv__(self, other: Number) -> NumberExpression:
        return Arithmetic("divide", other, self)

    def __lt__(self, other: Number) -> Condition:
        return Comparison("lt", self, other)

    def __gt__(self, other: Number) -> Condition:
        return Comparison("gt", self, other)

    def __le__(self, other: Number) -> Condition:
        return ~(self > other)

    def __ge__(self, other: Number) -> Condition:
        return ~(self < other)

    def equals(self, other: Value) -> Condition:
        return Comparison("equals", self, other)

    def __bool__(self) -> bool:
        raise TypeError("Game expressions cannot be evaluated by Python at build time")


type Number = float | NumberExpression


@dataclass(frozen=True, eq=False)
class Arithmetic(NumberExpression):
    operator: Literal["add", "subtract", "multiply", "divide"]
    left: Number | Condition
    right: Number | Condition


@dataclass(frozen=True, eq=False)
class RandomNumber(NumberExpression):
    low: Number
    high: Number


def random_number(low: Number, high: Number) -> NumberExpression:
    return RandomNumber(low, high)


@dataclass(frozen=True)
class Wait:
    seconds: Number


def wait(seconds: Number) -> Wait:
    return Wait(seconds)


@dataclass(frozen=True, eq=False)
class Comparison(Condition):
    operator: Literal["lt", "gt", "equals"]
    left: Value
    right: Value


@dataclass(frozen=True, eq=False)
class Logic(Condition):
    operator: Literal["and", "or"]
    left: Condition
    right: Condition


@dataclass(frozen=True, eq=False)
class Not(Condition):
    condition: Condition


@dataclass(frozen=True, eq=False)
class KeyDown(Condition):
    key: Key | str


@dataclass(frozen=True, eq=False)
class Touching(Condition):
    target: str


def key_down(key: Key | str) -> Condition:
    return KeyDown(key)


def touching(target: Sprite | str) -> Condition:
    return Touching(target.name if isinstance(target, Sprite) else target)


@dataclass(frozen=True, eq=False)
class NumberVariable(NumberExpression):
    name: str
    initial: float = 0
    id: str | None = None

    def set(self, value: Number) -> SetVariable:
        return SetVariable(self, value)

    def add(self, value: Number) -> ChangeVariable:
        return ChangeVariable(self, value)

    def reset(self) -> SetVariable:
        return self.set(self.initial)

    def show(self) -> NativeCommand:
        return block("data_showvariable", fields={"VARIABLE": self})

    def hide(self) -> NativeCommand:
        return block("data_hidevariable", fields={"VARIABLE": self})


@dataclass(frozen=True)
class GoTo:
    x: Number
    y: Number


@dataclass(frozen=True)
class MoveX:
    distance: Number


@dataclass(frozen=True)
class SetVariable:
    variable: NumberVariable
    value: Number


@dataclass(frozen=True)
class ChangeVariable:
    variable: NumberVariable
    value: Number


@dataclass(frozen=True)
class Repeat:
    times: Number
    body: tuple[Command, ...]


@dataclass(frozen=True)
class If:
    condition: Condition
    then: tuple[Command, ...]
    otherwise: tuple[Command, ...] | None = None
    _elif_chain: bool = False

    def else_(self, *steps: Steps) -> If:
        """Return a complete two-branch command without mutating this branch."""
        if self._elif_chain:
            assert self.otherwise is not None and isinstance(self.otherwise[0], If)
            return If(self.condition, self.then, (self.otherwise[0].else_(*steps),), True)
        return If(self.condition, self.then, flatten(steps))

    def elif_(self, condition: Condition) -> ElifBuilder:
        return ElifBuilder(self, condition)

    def _append_elif(self, branch: If) -> If:
        if self._elif_chain:
            assert self.otherwise is not None and isinstance(self.otherwise[0], If)
            return If(self.condition, self.then, (self.otherwise[0]._append_elif(branch),), True)
        if self.otherwise is not None:
            raise ValueError("elif_ must precede else_")
        return If(self.condition, self.then, (branch,), True)


@dataclass(frozen=True)
class ElifBuilder:
    root: If
    condition: Condition

    def then(self, *steps: Steps) -> If:
        return self.root._append_elif(If(self.condition, flatten(steps)))


@dataclass(frozen=True)
class IfBuilder:
    condition: Condition

    def then(self, *steps: Steps) -> If:
        return If(self.condition, flatten(steps))


def if_(condition: Condition) -> IfBuilder:
    return IfBuilder(condition)


@dataclass(frozen=True)
class Forever:
    body: tuple[Command, ...]


@dataclass(frozen=True)
class RepeatUntil:
    condition: Condition
    body: tuple[Command, ...]


@dataclass(frozen=True)
class Visibility:
    visible: bool


type Command = NativeCommand | ProcedureCall | GoTo | MoveX | SetVariable | ChangeVariable | Repeat | If | Forever | RepeatUntil | Visibility | PlaySound | Broadcast | Wait
type Steps = Command | Sequence[Steps]


def flatten(steps: tuple[Steps, ...]) -> tuple[Command, ...]:
    result: list[Command] = []
    for step in steps:
        match step:
            case Sequence():
                result.extend(flatten(tuple(step)))
            case NativeCommand() | ProcedureCall() | GoTo() | MoveX() | SetVariable() | ChangeVariable() | Repeat() | If() | Forever() | RepeatUntil() | Visibility() | PlaySound() | Broadcast() | Wait():
                result.append(step)
            case _:
                assert_never(step)
    return tuple(result)


@dataclass(frozen=True)
class Message:
    name: str
    id: str | None = None


@dataclass(frozen=True)
class Broadcast:
    message: Message
    wait: bool = False


def broadcast(message: Message, *, wait: bool = False) -> Broadcast:
    return Broadcast(message, wait)


def on_message(message: Message, *steps: Steps) -> Script:
    return Script(None, flatten(steps), message)


@dataclass(frozen=True)
class Script:
    key: Key | str | None
    body: tuple[Command, ...]
    message: Message | None = None
    clicked: bool = False
    event: NativeCommand | None = None
    detached: bool = False


@dataclass(frozen=True)
class Costume:
    svg: str | Path
    center_x: float = 20
    center_y: float = 20
    name: str = ""
    bitmap_resolution: float = 1


@dataclass(frozen=True)
class Sound:
    name: str
    source: Path
    rate: int = 0
    sample_count: int = 0
    format: str = ""


@dataclass(frozen=True)
class PlaySound:
    sound: Sound
    wait: bool = False


def play_sound(sound: Sound | Value | Menu, *, wait: bool = False) -> PlaySound | NativeCommand:
    if isinstance(sound, Sound):
        return PlaySound(sound, wait)
    return block("sound_playuntildone" if wait else "sound_play", inputs={"SOUND_MENU": sound})


@dataclass(frozen=True)
class Sprite:
    name: str
    costume: Costume
    scripts: tuple[Script, ...]
    x: float = 0
    y: float = 0
    sounds: tuple[Sound, ...] = ()
    costumes: tuple[Costume, ...] = ()
    procedures: tuple[Procedure, ...] = ()
    variables: tuple[NumberVariable | StringVariable, ...] = ()
    lists: tuple[ScratchList, ...] = ()
    size: float = 100
    direction: float = 90
    visible: bool = True
    current_costume: int = 0
    rotation_style: str = "all around"
    draggable: bool = False
    layer_order: int | None = None
    volume: float = 100


@dataclass(frozen=True)
class Game:
    name: str
    variables: tuple[NumberVariable | StringVariable, ...]
    sprites: tuple[Sprite, ...]
    messages: tuple[Message, ...] = ()
    lists: tuple[ScratchList, ...] = ()
    extensions: tuple[str, ...] = ()
    stage: Sprite | None = None
    monitors: tuple[dict[str, object], ...] = ()
    meta: dict[str, object] | None = None
    tempo: float = 60
    video_transparency: float = 50
    video_state: str = "on"
    text_to_speech_language: str | None = None


def on_start(*steps: Steps) -> Script:
    return Script(None, flatten(steps))


def on_key(key: Key | str, *steps: Steps) -> Script:
    return Script(key, flatten(steps))


def go_to(x: Number, y: Number) -> GoTo:
    return GoTo(x, y)


def move_x(distance: Number) -> MoveX:
    return MoveX(distance)


def repeat(times: Number, *steps: Steps) -> Repeat:
    return Repeat(times, flatten(steps))


def action[**P](generate: Callable[P, Steps]) -> Callable[P, tuple[Command, ...]]:
    """A typed build-time block generator; expands into ordinary Scratch blocks."""
    def expand(*args: P.args, **kwargs: P.kwargs) -> tuple[Command, ...]:
        return flatten((generate(*args, **kwargs),))
    return expand


def horizontal_controls(
    *, step: float, left: Key = Key.LEFT, right: Key = Key.RIGHT,
) -> tuple[Script, ...]:
    """Generate key events; movement is per event, including OS repeats."""
    return (on_key(left, move_x(-step)), on_key(right, move_x(step)))


def if_then(condition: Condition, *steps: Steps) -> If:
    return If(condition, flatten(steps))


def if_else(condition: Condition, *, then: Steps, otherwise: Steps) -> If:
    return If(condition, flatten((then,)), flatten((otherwise,)))


def forever(*steps: Steps) -> Forever:
    return Forever(flatten(steps))


def repeat_until(condition: Condition, *steps: Steps) -> RepeatUntil:
    return RepeatUntil(condition, flatten(steps))


def hide() -> Visibility:
    return Visibility(False)


def show() -> Visibility:
    return Visibility(True)



def on_click(*steps: Steps) -> Script:
    return Script(None, flatten(steps), clicked=True)


@dataclass(frozen=True, eq=False)
class ScratchLiteral(NumberExpression):
    type: int
    value: str
    id: str | None = None


# Native blocks use the input/field names from Scratch's block definitions.
type Value = str | Number | Condition | StringVariable | NativeReporter | NativeCondition | Argument | ScratchList | ScratchLiteral
type FieldValue = str | NumberVariable | StringVariable | ScratchList


@dataclass(frozen=True)
class Menu:
    opcode: str
    field: str
    value: str
    id: str | None = None


@dataclass(frozen=True)
class NativeCommand:
    opcode: str
    inputs: dict[str, Value | Menu]
    fields: dict[str, FieldValue]
    substacks: dict[str, tuple[Command, ...]]


@dataclass(frozen=True, eq=False)
class NativeReporter(NumberExpression):
    opcode: str
    inputs: dict[str, Value | Menu]
    fields: dict[str, FieldValue]


@dataclass(frozen=True, eq=False)
class NativeCondition(Condition):
    opcode: str
    inputs: dict[str, Value | Menu]
    fields: dict[str, FieldValue]


def block(opcode: str, *, inputs: dict[str, Value | Menu] | None = None,
          fields: dict[str, FieldValue] | None = None,
          substacks: dict[str, tuple[Command, ...]] | None = None) -> NativeCommand:
    return NativeCommand(opcode, inputs or {}, fields or {}, substacks or {})


def reporter(opcode: str, *, inputs: dict[str, Value | Menu] | None = None,
             fields: dict[str, FieldValue] | None = None) -> NativeReporter:
    return NativeReporter(opcode, inputs or {}, fields or {})


def predicate(opcode: str, *, inputs: dict[str, Value | Menu] | None = None,
              fields: dict[str, FieldValue] | None = None) -> NativeCondition:
    return NativeCondition(opcode, inputs or {}, fields or {})


def on_event(event: NativeCommand, *steps: Steps) -> Script:
    return Script(None, flatten(steps), event=event)


@dataclass(eq=False)
class StringVariable(NumberExpression):
    name: str
    initial: str = ""
    id: str | None = None

    def set(self, value: Value) -> NativeCommand:
        return block("data_setvariableto", inputs={"VALUE": value}, fields={"VARIABLE": self})

    def add(self, value: Number) -> NativeCommand:
        return block("data_changevariableby", inputs={"VALUE": value}, fields={"VARIABLE": self})

    def equals(self, other: Value) -> NativeCondition:
        return predicate("operator_equals", inputs={"OPERAND1": self, "OPERAND2": other})

    def show(self) -> NativeCommand:
        return block("data_showvariable", fields={"VARIABLE": self})

    def hide(self) -> NativeCommand:
        return block("data_hidevariable", fields={"VARIABLE": self})


@dataclass(frozen=True, eq=False)
class ScratchList:
    name: str
    initial: tuple[str | float, ...] = ()
    id: str | None = None

    def append(self, value: Value) -> NativeCommand:
        return block("data_addtolist", inputs={"ITEM": value}, fields={"LIST": self})

    def delete(self, index: Value) -> NativeCommand:
        return block("data_deleteoflist", inputs={"INDEX": index}, fields={"LIST": self})

    def clear(self) -> NativeCommand:
        return block("data_deletealloflist", fields={"LIST": self})

    def insert(self, index: Value, value: Value) -> NativeCommand:
        return block("data_insertatlist", inputs={"INDEX": index, "ITEM": value}, fields={"LIST": self})

    def replace(self, index: Value, value: Value) -> NativeCommand:
        return block("data_replaceitemoflist", inputs={"INDEX": index, "ITEM": value}, fields={"LIST": self})

    def item(self, index: Value) -> NativeReporter:
        return reporter("data_itemoflist", inputs={"INDEX": index}, fields={"LIST": self})

    def length(self) -> NativeReporter:
        return reporter("data_lengthoflist", fields={"LIST": self})

    def index(self, value: Value) -> NativeReporter:
        return reporter("data_itemnumoflist", inputs={"ITEM": value}, fields={"LIST": self})

    def contains(self, value: Value) -> NativeCondition:
        return predicate("data_listcontainsitem", inputs={"ITEM": value}, fields={"LIST": self})

    def show(self) -> NativeCommand:
        return block("data_showlist", fields={"LIST": self})

    def hide(self) -> NativeCommand:
        return block("data_hidelist", fields={"LIST": self})


@dataclass(frozen=True, eq=False)
class Argument(NumberExpression):
    name: str
    boolean: bool = False
    imported: bool = False


@dataclass(eq=False)
class Procedure:
    name: str
    arguments: tuple[Argument, ...] = ()
    body: tuple[Command, ...] = ()
    warp: bool = False
    proccode: str | None = None
    argument_ids: tuple[str, ...] = ()
    argument_defaults: tuple[object, ...] = ()
    _generate: Callable[..., Steps] | None = None

    def build(self) -> None:
        if self._generate is not None:
            body = flatten((self._generate(*self.arguments),))
            self.body = body
            self._generate = None

    def __call__(self, *values: Value) -> ProcedureCall:
        if len(values) != len(self.arguments):
            raise ValueError(f"{self.name} expects {len(self.arguments)} arguments")
        return ProcedureCall(self, values)


@dataclass(frozen=True)
class ProcedureCall:
    procedure: Procedure
    values: tuple[Value, ...]


def procedure(*, warp: bool = False, name: str | None = None,
              proccode: str | None = None, argument_names: tuple[str, ...] = (),
              argument_ids: tuple[str, ...] = (),
              argument_defaults: tuple[object, ...] = ()) -> Callable[[Callable[..., Steps]], Procedure]:
    """Define a Scratch custom block; build its body lazily to allow recursive calls."""
    def decorate(generate: Callable[..., Steps]) -> Procedure:
        parameters = tuple(inspect.signature(generate).parameters.values())
        if any(parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY,
                                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
               for parameter in parameters):
            raise TypeError("Procedure parameters must be positional")
        if argument_names and len(argument_names) != len(parameters):
            raise ValueError("argument_names must match the function parameters")
        slots = re.findall(r"%[bs]", proccode) if proccode is not None else []
        arguments = tuple(
            Argument(argument_names[index] if argument_names else parameter.name,
                     boolean=(slots[index] == '%b' if index < len(slots)
                              else parameter.annotation in (bool, 'bool', Condition, 'Condition')))
            for index, parameter in enumerate(parameters)
        )
        defaults = argument_defaults or tuple(
            parameter.default if parameter.default is not inspect.Parameter.empty
            else False if argument.boolean else ''
            for parameter, argument in zip(parameters, arguments)
        )
        return Procedure(name or getattr(generate, '__name__', 'procedure'), arguments, warp=warp,
                         proccode=proccode, argument_ids=argument_ids,
                         argument_defaults=defaults, _generate=generate)
    return decorate


def move(steps: Number) -> NativeCommand:
    return block("motion_movesteps", inputs={"STEPS": steps})


def move_y(distance: Number) -> NativeCommand:
    return block("motion_changeyby", inputs={"DY": distance})


def turn(degrees: Number) -> NativeCommand:
    return block("motion_turnright", inputs={"DEGREES": degrees})


def turn_left(degrees: Number) -> NativeCommand:
    return block("motion_turnleft", inputs={"DEGREES": degrees})


def point_direction(direction: Number) -> NativeCommand:
    return block("motion_pointindirection", inputs={"DIRECTION": direction})


def set_x(x: Number) -> NativeCommand:
    return block("motion_setx", inputs={"X": x})


def set_y(y: Number) -> NativeCommand:
    return block("motion_sety", inputs={"Y": y})


def glide(seconds: Number, x: Number, y: Number) -> NativeCommand:
    return block("motion_glidesecstoxy", inputs={"SECS": seconds, "X": x, "Y": y})


def bounce() -> NativeCommand:
    return block("motion_ifonedgebounce")


def say(message: Value, seconds: Number | None = None) -> NativeCommand:
    return block("looks_say" if seconds is None else "looks_sayforsecs",
                 inputs={"MESSAGE": message} if seconds is None else {"MESSAGE": message, "SECS": seconds})


def think(message: Value, seconds: Number | None = None) -> NativeCommand:
    return block("looks_think" if seconds is None else "looks_thinkforsecs",
                 inputs={"MESSAGE": message} if seconds is None else {"MESSAGE": message, "SECS": seconds})


def switch_costume(name: Value | Menu) -> NativeCommand:
    costume = Menu("looks_costume", "COSTUME", name) if isinstance(name, str) else name
    return block("looks_switchcostumeto", inputs={"COSTUME": costume})


def next_costume() -> NativeCommand:
    return block("looks_nextcostume")


def set_size(size: Number) -> NativeCommand:
    return block("looks_setsizeto", inputs={"SIZE": size})


def clone(target: Sprite | str | Value | Menu = "_myself_") -> NativeCommand:
    clone_target = Menu("control_create_clone_of_menu", "CLONE_OPTION", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("control_create_clone_of", inputs={"CLONE_OPTION": clone_target})


def delete_clone() -> NativeCommand:
    return block("control_delete_this_clone")


def on_clone(*steps: Steps) -> Script:
    return on_event(block("control_start_as_clone"), *steps)


def join(left: Value, right: Value, *parts: Value) -> NativeReporter:
    """Concatenate values using left-nested Scratch join blocks."""
    result = reporter("operator_join", inputs={"STRING1": left, "STRING2": right})
    for part in parts:
        result = reporter("operator_join", inputs={"STRING1": result, "STRING2": part})
    return result


def letter(index: Value, text: Value) -> NativeReporter:
    return reporter("operator_letter_of", inputs={"LETTER": index, "STRING": text})


def length(text: Value) -> NativeReporter:
    return reporter("operator_length", inputs={"STRING": text})


def contains(text: Value, part: Value) -> NativeCondition:
    return predicate("operator_contains", inputs={"STRING1": text, "STRING2": part})


def go_to_target(target: Sprite | str | Value | Menu) -> NativeCommand:
    destination = Menu("motion_goto_menu", "TO", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("motion_goto", inputs={"TO": destination})


def point_towards(target: Sprite | str | Value | Menu) -> NativeCommand:
    destination = Menu("motion_pointtowards_menu", "TOWARDS", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("motion_pointtowards", inputs={"TOWARDS": destination})


def rotation_style(style: Literal["all around", "left-right", "don't rotate"]) -> NativeCommand:
    return block("motion_setrotationstyle", fields={"STYLE": style})


def change_size(amount: Number) -> NativeCommand:
    return block("looks_changesizeby", inputs={"CHANGE": amount})


def set_effect(effect: str, value: Number) -> NativeCommand:
    return block("looks_seteffectto", inputs={"VALUE": value}, fields={"EFFECT": effect})


def change_effect(effect: str, amount: Number) -> NativeCommand:
    return block("looks_changeeffectby", inputs={"CHANGE": amount}, fields={"EFFECT": effect})


def clear_effects() -> NativeCommand:
    return block("looks_cleargraphiceffects")


def stop_sounds() -> NativeCommand:
    return block("sound_stopallsounds")


def set_volume(value: Number) -> NativeCommand:
    return block("sound_setvolumeto", inputs={"VOLUME": value})


def change_volume(amount: Number) -> NativeCommand:
    return block("sound_changevolumeby", inputs={"VOLUME": amount})


def wait_until(condition: Condition) -> NativeCommand:
    return block("control_wait_until", inputs={"CONDITION": condition})


def stop(option: Literal["all", "this script", "other scripts in sprite"] = "all") -> NativeCommand:
    return block("control_stop", fields={"STOP_OPTION": option})


def ask(question: Value) -> NativeCommand:
    return block("sensing_askandwait", inputs={"QUESTION": question})


def answer() -> NativeReporter:
    return reporter("sensing_answer")


def mouse_x() -> NativeReporter:
    return reporter("sensing_mousex")


def mouse_y() -> NativeReporter:
    return reporter("sensing_mousey")


def mouse_down() -> NativeCondition:
    return predicate("sensing_mousedown")


def timer() -> NativeReporter:
    return reporter("sensing_timer")


def reset_timer() -> NativeCommand:
    return block("sensing_resettimer")


def x_position() -> NativeReporter:
    return reporter("motion_xposition")


def y_position() -> NativeReporter:
    return reporter("motion_yposition")


def direction() -> NativeReporter:
    return reporter("motion_direction")


def modulo(left: Number, right: Number) -> NativeReporter:
    return reporter("operator_mod", inputs={"NUM1": left, "NUM2": right})


def round_number(value: Number) -> NativeReporter:
    return reporter("operator_round", inputs={"NUM": value})


def math_op(operation: str, value: Number) -> NativeReporter:
    return reporter("operator_mathop", inputs={"NUM": value}, fields={"OPERATOR": operation})


def abs_number(value: Number) -> NativeReporter:
    return math_op('abs', value)


def floor(value: Number) -> NativeReporter:
    return math_op('floor', value)


def ceil(value: Number) -> NativeReporter:
    return math_op('ceiling', value)


def sqrt(value: Number) -> NativeReporter:
    return math_op('sqrt', value)


def sin(value: Number) -> NativeReporter:
    """Scratch sin; angles are in degrees."""
    return math_op('sin', value)


def cos(value: Number) -> NativeReporter:
    """Scratch cos; angles are in degrees."""
    return math_op('cos', value)


def tan(value: Number) -> NativeReporter:
    """Scratch tan; angles are in degrees."""
    return math_op('tan', value)


def asin(value: Number) -> NativeReporter:
    """Scratch asin; angles are in degrees."""
    return math_op('asin', value)


def acos(value: Number) -> NativeReporter:
    """Scratch acos; angles are in degrees."""
    return math_op('acos', value)


def atan(value: Number) -> NativeReporter:
    """Scratch atan; angles are in degrees."""
    return math_op('atan', value)


def ln(value: Number) -> NativeReporter:
    return math_op('ln', value)


def log10(value: Number) -> NativeReporter:
    return math_op('log', value)


def exp(value: Number) -> NativeReporter:
    return math_op('e ^', value)


def pow10(value: Number) -> NativeReporter:
    return math_op('10 ^', value)


def stamp() -> NativeCommand:
    return block("pen_stamp")


def pen_up() -> NativeCommand:
    return block("pen_penUp")


def pen_down() -> NativeCommand:
    return block("pen_penDown")


def clear_pen() -> NativeCommand:
    return block("pen_clear")


def set_pen_size(size: Number) -> NativeCommand:
    return block("pen_setPenSizeTo", inputs={"SIZE": size})


def set_pen_color(color: Value) -> NativeCommand:
    return block("pen_setPenColorToColor", inputs={"COLOR": color})


def set_pen_color_param(parameter: str, value: Number) -> NativeCommand:
    return block("pen_setPenColorParamTo", inputs={"VALUE": value}, fields={"COLOR_PARAM": parameter})


def costume_number_or_name(mode: str) -> NativeReporter:
    return reporter("looks_costumenumbername", fields={"NUMBER_NAME": mode})


def set_drag_mode(mode: str) -> NativeCommand:
    return block("sensing_setdragmode", fields={"DRAG_MODE": mode})


def property_of(target: Value | Menu, property_name: str) -> NativeReporter:
    return reporter("sensing_of", inputs={"OBJECT": target}, fields={"PROPERTY": property_name})


def round_number(value: Number) -> NativeReporter:
    return reporter("operator_round", inputs={"NUM": value})


def math_function(function: str, value: Number) -> NativeReporter:
    return reporter("operator_mathop", inputs={"NUM": value}, fields={"OPERATOR": function})


def switch_backdrop(name: Value | Menu, *, wait: bool = False) -> NativeCommand:
    backdrop = Menu("looks_backdrops", "BACKDROP", name) if isinstance(name, str) else name
    return block("looks_switchbackdroptoandwait" if wait else "looks_switchbackdropto",
                 inputs={"BACKDROP": backdrop})


def next_backdrop() -> NativeCommand:
    return block("looks_nextbackdrop")


def on_backdrop(name: str, *steps: Steps) -> Script:
    return on_event(block("event_whenbackdropswitchesto", fields={"BACKDROP": name}), *steps)
