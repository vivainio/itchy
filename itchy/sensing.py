"""Scratch sensing builders."""
from __future__ import annotations
from typing import Literal
from itchy.game import (
    Condition, Key, KeyDown, Menu,
    NativeCommand, NativeCondition, NativeReporter, Sprite, Touching, Value, block, predicate, reporter,
)


def key_down(key: Key | str) -> Condition:
    return KeyDown(key)


def touching(target: Sprite | str) -> Condition:
    return Touching(target.name if isinstance(target, Sprite) else target)


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


def set_drag_mode(mode: str) -> NativeCommand:
    return block("sensing_setdragmode", fields={"DRAG_MODE": mode})


def property_of(target: Sprite | Value | Menu, property_name: str) -> NativeReporter:
    destination = Menu("sensing_of_object_menu", "OBJECT", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return reporter("sensing_of", inputs={"OBJECT": destination}, fields={"PROPERTY": property_name})


def touching_color(color: Value) -> NativeCondition:
    return predicate("sensing_touchingcolor", inputs={"COLOR": color})


def color_touching_color(color: Value, other: Value) -> NativeCondition:
    return predicate("sensing_coloristouchingcolor", inputs={"COLOR": color, "COLOR2": other})


def distance_to(target: Sprite | str | Value | Menu) -> NativeReporter:
    destination = Menu("sensing_distancetomenu", "DISTANCETOMENU", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return reporter("sensing_distanceto", inputs={"DISTANCETOMENU": destination})


def current(part: Literal["YEAR", "MONTH", "DATE", "DAYOFWEEK", "HOUR", "MINUTE", "SECOND"]) -> NativeReporter:
    return reporter("sensing_current", fields={"CURRENTMENU": part})


def days_since_2000() -> NativeReporter:
    return reporter("sensing_dayssince2000")


def loudness() -> NativeReporter:
    return reporter("sensing_loudness")


def loud() -> NativeCondition:
    return predicate("sensing_loud")


def username() -> NativeReporter:
    return reporter("sensing_username")
