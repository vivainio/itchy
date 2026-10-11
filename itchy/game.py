from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class Wait:
    seconds: Number


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


@dataclass(frozen=True, eq=False)
class Num(NumberExpression):
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
    variable: Num
    value: Number


@dataclass(frozen=True)
class ChangeVariable:
    variable: Num
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

    def then_(self, *steps: Steps) -> If:
        return self.root._append_elif(If(self.condition, flatten(steps)))


@dataclass(frozen=True)
class IfBuilder:
    condition: Condition

    def then_(self, *steps: Steps) -> If:
        return If(self.condition, flatten(steps))


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
    variables: tuple[Num | String, ...] = ()
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
class Monitor:
    target: Num | String | ScratchList
    x: float = 0
    y: float = 0
    visible: bool = False
    width: float = 0
    height: float = 0
    mode: str | None = None
    value: object = None
    slider_min: float = 0
    slider_max: float = 100
    is_discrete: bool = True


@dataclass(frozen=True)
class ReporterMonitor:
    opcode: str
    sprite_name: str | None = None
    params: dict[str, object] = field(default_factory=dict)
    x: float = 0
    y: float = 0
    visible: bool = False
    width: float = 0
    height: float = 0
    mode: str = "default"
    value: object = 0


@dataclass(frozen=True)
class Game:
    name: str
    variables: tuple[Num | String, ...]
    sprites: tuple[Sprite, ...]
    messages: tuple[Message, ...] = ()
    lists: tuple[ScratchList, ...] = ()
    extensions: tuple[str, ...] = ()
    stage: Sprite | None = None
    monitors: tuple[Monitor | ReporterMonitor | dict[str, object], ...] = ()
    meta: dict[str, object] | None = None
    tempo: float = 60
    video_transparency: float = 50
    video_state: str = "on"
    text_to_speech_language: str | None = None


def action[**P](generate: Callable[P, Steps]) -> Callable[P, tuple[Command, ...]]:
    """A typed build-time block generator; expands into ordinary Scratch blocks."""
    def expand(*args: P.args, **kwargs: P.kwargs) -> tuple[Command, ...]:
        return flatten((generate(*args, **kwargs),))
    return expand


@dataclass(frozen=True, eq=False)
class ScratchLiteral(NumberExpression):
    type: int
    value: str
    id: str | None = None


# Native blocks use the input/field names from Scratch's block definitions.
type Value = str | Number | Condition | String | NativeReporter | NativeCondition | Argument | ScratchList | ScratchLiteral
type FieldValue = str | Num | String | ScratchList


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


@dataclass(eq=False)
class String(NumberExpression):
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


