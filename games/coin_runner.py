from itchy import events
from itchy import move
from pathlib import Path

from itchy.game import Costume, Game, Key, Num, Sprite, action

score = Num("score", initial=0)
assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")


@action
def reset_player():
    return move.to(0, 0), score.reset()


@action
def award_points(points: float):
    return score.add(points)


game = Game(
    name="Coin Runner",
    variables=(score,),
    sprites=(
        Sprite(
            name="Player",
            costume=player_costume,
            scripts=(
                events.on_start(reset_player()),
                *move.horizontal_controls(step=10),
                events.on_key(Key.SPACE, award_points(1)),
            ),
        ),
    ),
)
