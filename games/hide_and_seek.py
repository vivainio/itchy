# SPDX-License-Identifier: CC-BY-SA-2.0
# Adapted from Scratchteam's Hide and Seek (project 10128368).
# https://scratch.mit.edu/projects/10128368/
# Original artwork/sound replaced; instruction bubble omitted.
from pathlib import Path

from itchy.game import (
    Command, Costume, Game, NumberVariable, Sound, Sprite, forever, go_to, hide,
    on_click, on_start, play_sound, random_number, show, wait,
)

assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")
score = NumberVariable("score")
chime = Sound("Found", assets / "collect.wav")

reset_round: list[Command] = [score.reset(), go_to(0, 0), show()]
relocate = go_to(random_number(-200, 200), random_number(-140, 140))
hide_then_appear: list[Command] = [hide(), wait(1), relocate, show(), wait(0.7)]
found_target: list[Command] = [score.add(1), play_sound(chime), relocate]

target = Sprite(
    name="Target",
    costume=player_costume,
    sounds=(chime,),
    scripts=(
        on_start(reset_round, forever(hide_then_appear)),
        on_click(found_target),
    ),
)
game = Game("Hide and Seek — Python recreation", (score,), (target,))
