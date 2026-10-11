"""Scratch motion commands and reporters.

Use ``from itchy import move`` and call ``move.x(10)`` or ``move.to(0, 0)``.
"""
from itchy import events
from typing import Literal
from itchy import events

from itchy.game import GoTo, Key, Menu, MoveX, NativeCommand, NativeReporter, Number, Script, Sprite, Value, block, reporter


def to(x: Number, y: Number) -> GoTo:
    return GoTo(x, y)


def x(distance: Number) -> MoveX:
    return MoveX(distance)


def horizontal_controls(
    *, step: float, left: Key = Key.LEFT, right: Key = Key.RIGHT,
) -> tuple[Script, ...]:
    """Generate key events; movement is per event, including OS repeats."""
    return (events.on_key(left, x(-step)), events.on_key(right, x(step)))


def steps(steps: Number) -> NativeCommand:
    return block("motion_movesteps", inputs={"STEPS": steps})


def y(distance: Number) -> NativeCommand:
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


def to_target(target: Sprite | str | Value | Menu) -> NativeCommand:
    destination = Menu("motion_goto_menu", "TO", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("motion_goto", inputs={"TO": destination})


def point_towards(target: Sprite | str | Value | Menu) -> NativeCommand:
    destination = Menu("motion_pointtowards_menu", "TOWARDS", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("motion_pointtowards", inputs={"TOWARDS": destination})


def rotation_style(style: Literal["all around", "left-right", "don't rotate"]) -> NativeCommand:
    return block("motion_setrotationstyle", fields={"STYLE": style})


def x_position() -> NativeReporter:
    return reporter("motion_xposition")


def y_position() -> NativeReporter:
    return reporter("motion_yposition")


def direction() -> NativeReporter:
    return reporter("motion_direction")



def glide_to(seconds: Number, target: Sprite | str | Value | Menu) -> NativeCommand:
    destination = Menu("motion_glideto_menu", "TO", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("motion_glideto", inputs={"SECS": seconds, "TO": destination})
