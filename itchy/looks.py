"""Scratch looks builders."""
from __future__ import annotations
from typing import Literal
from itchy.game import (
    Menu,
    NativeCommand, NativeReporter, Number,
    Value, Visibility, block, reporter,
)


def hide() -> Visibility:
    return Visibility(False)


def show() -> Visibility:
    return Visibility(True)


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


def change_size(amount: Number) -> NativeCommand:
    return block("looks_changesizeby", inputs={"CHANGE": amount})


def set_effect(effect: str, value: Number) -> NativeCommand:
    return block("looks_seteffectto", inputs={"VALUE": value}, fields={"EFFECT": effect})


def change_effect(effect: str, amount: Number) -> NativeCommand:
    return block("looks_changeeffectby", inputs={"CHANGE": amount}, fields={"EFFECT": effect})


def clear_effects() -> NativeCommand:
    return block("looks_cleargraphiceffects")


def costume_number_or_name(mode: str) -> NativeReporter:
    return reporter("looks_costumenumbername", fields={"NUMBER_NAME": mode})


def switch_backdrop(name: Value | Menu, *, wait: bool = False) -> NativeCommand:
    backdrop = Menu("looks_backdrops", "BACKDROP", name) if isinstance(name, str) else name
    return block("looks_switchbackdroptoandwait" if wait else "looks_switchbackdropto",
                 inputs={"BACKDROP": backdrop})


def next_backdrop() -> NativeCommand:
    return block("looks_nextbackdrop")


def layer(position: Literal["front", "back"]) -> NativeCommand:
    return block("looks_gotofrontback", fields={"FRONT_BACK": position})


def change_layers(amount: Number, direction: Literal["forward", "backward"] = "forward") -> NativeCommand:
    return block("looks_goforwardbackwardlayers", inputs={"NUM": amount}, fields={"FORWARD_BACKWARD": direction})


def size() -> NativeReporter:
    return reporter("looks_size")


def backdrop_number_or_name(mode: Literal["number", "name"] = "number") -> NativeReporter:
    return reporter("looks_backdropnumbername", fields={"NUMBER_NAME": mode})
