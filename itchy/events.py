"""Scratch events builders."""
from __future__ import annotations
from typing import Literal
from itchy.game import (
    Broadcast, Key, Menu,
    Message, NativeCommand, Number,
    Script, Sprite, Steps, block, flatten,
)


def broadcast(message: Message, *, wait: bool = False) -> Broadcast:
    return Broadcast(message, wait)


def on_message(message: Message, *steps: Steps) -> Script:
    return Script(None, flatten(steps), message)


def on_start(*steps: Steps) -> Script:
    return Script(None, flatten(steps))


def on_key(key: Key | str, *steps: Steps) -> Script:
    return Script(key, flatten(steps))


def on_click(*steps: Steps) -> Script:
    return Script(None, flatten(steps), clicked=True)


def on_event(event: NativeCommand, *steps: Steps) -> Script:
    return Script(None, flatten(steps), event=event)


def on_clone(*steps: Steps) -> Script:
    return on_event(block("control_start_as_clone"), *steps)


def on_backdrop(name: str, *steps: Steps) -> Script:
    return on_event(block("event_whenbackdropswitchesto", fields={"BACKDROP": name}), *steps)


def on_stage_click(*steps: Steps) -> Script:
    return on_event(block("event_whenstageclicked"), *steps)


def on_greater_than(sensor: Literal["LOUDNESS", "TIMER"], value: Number, *steps: Steps) -> Script:
    return on_event(block("event_whengreaterthan", inputs={"VALUE": value}, fields={"WHENGREATERTHANMENU": sensor}), *steps)


def on_touching(target: Sprite | str, *steps: Steps) -> Script:
    destination = Menu("sensing_touchingobjectmenu", "TOUCHINGOBJECTMENU", target.name if isinstance(target, Sprite) else target)
    return on_event(block("event_whentouchingobject", inputs={"TOUCHINGOBJECTMENU": destination}), *steps)
