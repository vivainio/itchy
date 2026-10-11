from itchy import control, events, looks, operators, sound
from itchy import move
# SPDX-License-Identifier: CC-BY-SA-2.0
# Adapted from Scratchteam's Hide and Seek (project 10128368).
# https://scratch.mit.edu/projects/10128368/
# Original artwork/sound replaced; instruction bubble omitted.
from pathlib import Path

from itchy.game import Command, Costume, Game, Num, Sound, Sprite

assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")
score = Num("score")
chime = Sound("Found", assets / "collect.wav")

reset_round: list[Command] = [score.reset(), move.to(0, 0), looks.show()]
relocate = move.to(operators.random_number(-200, 200), operators.random_number(-140, 140))
hide_then_appear: list[Command] = [looks.hide(), control.wait(1), relocate, looks.show(), control.wait(0.7)]
found_target: list[Command] = [score.add(1), sound.play(chime), relocate]

target = Sprite(
    name="Target",
    costume=player_costume,
    sounds=(chime,),
    scripts=(
        events.on_start(reset_round, control.forever(hide_then_appear)),
        events.on_click(found_target),
    ),
)
game = Game("Hide and Seek — Python recreation", (score,), (target,))
