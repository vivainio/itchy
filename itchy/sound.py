"""Scratch sound builders."""
from __future__ import annotations
from typing import Literal
from itchy.game import (
    Menu,
    NativeCommand, NativeReporter, Number,
    PlaySound, Sound, Value, block, reporter,
)


def play(sound: Sound | Value | Menu, *, wait: bool = False) -> PlaySound | NativeCommand:
    if isinstance(sound, Sound):
        return PlaySound(sound, wait)
    selection = Menu("sound_sounds_menu", "SOUND_MENU", sound) if isinstance(sound, str) else sound
    return block("sound_playuntildone" if wait else "sound_play", inputs={"SOUND_MENU": selection})


def stop_all() -> NativeCommand:
    return block("sound_stopallsounds")


def set_volume(value: Number) -> NativeCommand:
    return block("sound_setvolumeto", inputs={"VOLUME": value})


def change_volume(amount: Number) -> NativeCommand:
    return block("sound_changevolumeby", inputs={"VOLUME": amount})


def set_effect(effect: Literal["pitch", "pan left/right"], value: Number) -> NativeCommand:
    return block("sound_seteffectto", inputs={"VALUE": value}, fields={"EFFECT": effect})


def change_effect(effect: Literal["pitch", "pan left/right"], amount: Number) -> NativeCommand:
    return block("sound_changeeffectby", inputs={"VALUE": amount}, fields={"EFFECT": effect})


def clear_effects() -> NativeCommand:
    return block("sound_cleareffects")


def volume() -> NativeReporter:
    return reporter("sound_volume")
