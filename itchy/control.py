"""Scratch control builders."""
from __future__ import annotations
from typing import Literal
from itchy.game import (
    Condition, Forever, If, IfBuilder, Menu,
    NativeCommand, NativeReporter, Number,
    Num, Repeat, RepeatUntil,
    Sprite, Steps, Value, Wait,
    block, flatten, reporter,
)


def wait(seconds: Number) -> Wait:
    return Wait(seconds)


def if_(condition: Condition) -> IfBuilder:
    return IfBuilder(condition)


def repeat(times: Number, *steps: Steps) -> Repeat:
    return Repeat(times, flatten(steps))


def if_then(condition: Condition, *steps: Steps) -> If:
    return If(condition, flatten(steps))


def if_else(condition: Condition, *, then: Steps, otherwise: Steps) -> If:
    return If(condition, flatten((then,)), flatten((otherwise,)))


def forever(*steps: Steps) -> Forever:
    return Forever(flatten(steps))


def repeat_until(condition: Condition, *steps: Steps) -> RepeatUntil:
    return RepeatUntil(condition, flatten(steps))


def clone(target: Sprite | str | Value | Menu = "_myself_") -> NativeCommand:
    clone_target = Menu("control_create_clone_of_menu", "CLONE_OPTION", target.name if isinstance(target, Sprite) else target) if isinstance(target, (Sprite, str)) else target
    return block("control_create_clone_of", inputs={"CLONE_OPTION": clone_target})


def delete_clone() -> NativeCommand:
    return block("control_delete_this_clone")


def wait_until(condition: Condition) -> NativeCommand:
    return block("control_wait_until", inputs={"CONDITION": condition})


def stop(option: Literal["all", "this script", "other scripts in sprite"] = "all") -> NativeCommand:
    return block("control_stop", fields={"STOP_OPTION": option})


def while_(condition: Condition, *steps: Steps) -> NativeCommand:
    return block("control_while", inputs={"CONDITION": condition}, substacks={"SUBSTACK": flatten(steps)})


def for_each(variable: Num, count: Number, *steps: Steps) -> NativeCommand:
    return block("control_for_each", inputs={"VALUE": count}, fields={"VARIABLE": variable}, substacks={"SUBSTACK": flatten(steps)})


def counter() -> NativeReporter:
    return reporter("control_get_counter")


def increment_counter() -> NativeCommand:
    return block("control_incr_counter")


def clear_counter() -> NativeCommand:
    return block("control_clear_counter")


def all_at_once(*steps: Steps) -> NativeCommand:
    return block("control_all_at_once", substacks={"SUBSTACK": flatten(steps)})
