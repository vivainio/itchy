from itchy.game import (
    Costume, Game, Key, NumberVariable, Sprite, action, go_to,
    horizontal_controls, on_key, on_start,
)

score = NumberVariable("score", initial=0)
player_costume = Costume(
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
    '<rect x="2" y="2" width="36" height="36" rx="10" fill="#7c3aed"/>'
    '<circle cx="14" cy="15" r="3" fill="white"/>'
    '<circle cx="26" cy="15" r="3" fill="white"/></svg>'
)


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
