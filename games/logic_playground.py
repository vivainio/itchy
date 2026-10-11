from itchy import control, events, looks, sensing, sound
from itchy import move
"""A real collectible: collision detection, score, hiding, and restart."""
from pathlib import Path

from itchy.game import Command, Costume, Game, Message, Num, Sound, Sprite

assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")
collect_sound = Sound("Collect", assets / "collect.wav")
score = Num("score")
collected = Num("collected")
ready = Message("ready")
reset_player: list[Command] = [move.to(0, 0), score.reset(), events.broadcast(ready)]
prepare_coin: list[Command] = [move.to(80, 0), collected.reset(), looks.show()]
collect_coin: list[Command] = [score.add(1), collected.set(1), sound.play(collect_sound), looks.hide()]

player = Sprite("Player", player_costume, (
    events.on_start(reset_player),
    *move.horizontal_controls(step=10),
))
watch_for_player = control.forever(
    control.if_(collected.equals(0) & sensing.touching(player)).then_(collect_coin),
)
coin = Sprite("Coin", Costume(assets / "coin.png"), (
    events.on_message(ready, prepare_coin, watch_for_player),
), sounds=(collect_sound,))
game = Game("Logic Playground", (score, collected), (player, coin), messages=(ready,))
