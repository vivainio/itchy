from pathlib import Path

from itchy.game import (
    Costume, Game, Key, Num, Sprite, action, go_to,
    horizontal_controls, on_key, on_start,
)

score = Num("score", initial=0)
assets = Path(__file__).parent / "assets"
player_costume = Costume(assets / "player.svg")


@action
def reset_player():
    return go_to(0, 0), score.reset()


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
                on_start(reset_player()),
                *horizontal_controls(step=10),
                on_key(Key.SPACE, award_points(1)),
            ),
        ),
    ),
)
