from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
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

    def equals(self, other: Number) -> Condition:
        return Comparison("equals", self, other)

    def __bool__(self) -> bool:
        raise TypeError("Game expressions cannot be evaluated by Python at build time")


type Number = float | NumberExpression


@dataclass(frozen=True, eq=False)
class Arithmetic(NumberExpression):
    operator: Literal["add", "subtract", "multiply", "divide"]
    left: Number
    right: Number


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
    left: Number
    right: Number


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
    key: Key


@dataclass(frozen=True, eq=False)
class Touching(Condition):
    target: str


def key_down(key: Key) -> Condition:
    return KeyDown(key)


def touching(target: Sprite | str) -> Condition:
    return Touching(target.name if isinstance(target, Sprite) else target)


@dataclass(frozen=True, eq=False)
class NumberVariable(NumberExpression):
    name: str
    initial: float = 0

    def set(self, value: Number) -> SetVariable:
        return SetVariable(self, value)

    def add(self, value: Number) -> ChangeVariable:
        return ChangeVariable(self, value)

    def reset(self) -> SetVariable:
        return self.set(self.initial)


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
    times: int
    body: tuple[Command, ...]


@dataclass(frozen=True)
class If:
    condition: Condition
    then: tuple[Command, ...]
    otherwise: tuple[Command, ...] | None = None

    def else_(self, *steps: Steps) -> If:
        """Return a complete two-branch command without mutating this branch."""
        return If(self.condition, self.then, flatten(steps))


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


type Command = GoTo | MoveX | SetVariable | ChangeVariable | Repeat | If | Forever | RepeatUntil | Visibility | PlaySound | Broadcast | Wait
type Steps = Command | Sequence[Steps]


def flatten(steps: tuple[Steps, ...]) -> tuple[Command, ...]:
    result: list[Command] = []
    for step in steps:
        match step:
            case Sequence():
                result.extend(flatten(tuple(step)))
            case GoTo() | MoveX() | SetVariable() | ChangeVariable() | Repeat() | If() | Forever() | RepeatUntil() | Visibility() | PlaySound() | Broadcast() | Wait():
                result.append(step)
            case _:
                assert_never(step)
    return tuple(result)


@dataclass(frozen=True)
class Message:
    name: str


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
    key: Key | None
    body: tuple[Command, ...]
    message: Message | None = None
    clicked: bool = False


@dataclass(frozen=True)
class Costume:
    svg: str | Path
    center_x: float = 20
    center_y: float = 20


@dataclass(frozen=True)
class Sound:
    name: str
    source: Path
    rate: int = 0
    sample_count: int = 0


@dataclass(frozen=True)
class PlaySound:
    sound: Sound
    wait: bool = False


def play_sound(sound: Sound, *, wait: bool = False) -> PlaySound:
    return PlaySound(sound, wait)


@dataclass(frozen=True)
class Sprite:
    name: str
    costume: Costume
    scripts: tuple[Script, ...]
    x: float = 0
    y: float = 0
    sounds: tuple[Sound, ...] = ()
    costumes: tuple[Costume, ...] = ()


@dataclass(frozen=True)
class Game:
    name: str
    variables: tuple[NumberVariable, ...]
    sprites: tuple[Sprite, ...]
    messages: tuple[Message, ...] = ()


def on_start(*steps: Steps) -> Script:
    return Script(None, flatten(steps))


def on_key(key: Key, *steps: Steps) -> Script:
    return Script(key, flatten(steps))


def go_to(x: Number, y: Number) -> GoTo:
    return GoTo(x, y)


def move_x(distance: Number) -> MoveX:
    return MoveX(distance)


def repeat(times: int, *steps: Steps) -> Repeat:
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
