"""A real collectible: collision detection, score, hiding, and restart."""
from pathlib import Path

from itchy.game import (
    Command, Costume, Game, Message, broadcast, on_message, NumberVariable, Sound, Sprite, play_sound, forever, go_to, hide,
    horizontal_controls, if_, on_start, show, touching,
)

assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")
collect_sound = Sound("Collect", assets / "collect.wav")
score = NumberVariable("score")
collected = NumberVariable("collected")
ready = Message("ready")
reset_player: list[Command] = [go_to(0, 0), score.reset(), broadcast(ready)]
prepare_coin: list[Command] = [go_to(80, 0), collected.reset(), show()]
collect_coin: list[Command] = [score.add(1), collected.set(1), play_sound(collect_sound), hide()]

player = Sprite("Player", player_costume, (
    on_start(reset_player),
    *horizontal_controls(step=10),
))
watch_for_player = forever(
    if_(collected.equals(0) & touching(player)).then(collect_coin),
)
coin = Sprite("Coin", Costume(assets / "coin.png"), (
    on_message(ready, prepare_coin, watch_for_player),
), sounds=(collect_sound,))
game = Game("Logic Playground", (score, collected), (player, coin), messages=(ready,))
