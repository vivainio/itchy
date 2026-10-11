from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never


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


@dataclass(frozen=True)
class NumberVariable:
    name: str
    initial: float = 0

    def set(self, value: float) -> SetVariable:
        return SetVariable(self, value)

    def add(self, value: float) -> ChangeVariable:
        return ChangeVariable(self, value)

    def reset(self) -> SetVariable:
        return self.set(self.initial)


@dataclass(frozen=True)
class GoTo:
    x: float
    y: float


@dataclass(frozen=True)
class MoveX:
    distance: float


@dataclass(frozen=True)
class SetVariable:
    variable: NumberVariable
    value: float


@dataclass(frozen=True)
class ChangeVariable:
    variable: NumberVariable
    value: float


@dataclass(frozen=True)
class Repeat:
    times: int
    body: tuple[Command, ...]


type Command = GoTo | MoveX | SetVariable | ChangeVariable | Repeat
type Steps = Command | list[Steps] | tuple[Steps, ...]


def flatten(steps: tuple[Steps, ...]) -> tuple[Command, ...]:
    result: list[Command] = []
    for step in steps:
        match step:
            case list() | tuple():
                result.extend(flatten(tuple(step)))
            case GoTo() | MoveX() | SetVariable() | ChangeVariable() | Repeat():
                result.append(step)
            case _:
                assert_never(step)
    return tuple(result)


@dataclass(frozen=True)
class Script:
    key: Key | None
    body: tuple[Command, ...]


@dataclass(frozen=True)
class Costume:
    svg: str
    center_x: float = 20
    center_y: float = 20


@dataclass(frozen=True)
class Sprite:
    name: str
    costume: Costume
    scripts: tuple[Script, ...]
    x: float = 0
    y: float = 0


@dataclass(frozen=True)
class Game:
    name: str
    variables: tuple[NumberVariable, ...]
    sprites: tuple[Sprite, ...]


def on_start(*steps: Steps) -> Script:
    return Script(None, flatten(steps))


def on_key(key: Key, *steps: Steps) -> Script:
    return Script(key, flatten(steps))


def go_to(x: float, y: float) -> GoTo:
    return GoTo(x, y)


def move_x(distance: float) -> MoveX:
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
