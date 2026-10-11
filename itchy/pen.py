"""Scratch pen builders."""
from __future__ import annotations
from itchy.game import (
    NativeCommand, Number,
    Value, block,
)


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
