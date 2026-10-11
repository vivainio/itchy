# Game structure

A `Game` contains declared variables, sprites, and optional messages. Each sprite contains costumes, sounds, and event scripts. Frozen dataclasses keep the authored description separate from execution state.

```python
from itchy.game import (
    Costume, Game, Key, NumberVariable, Sprite,
    go_to, move_x, on_key, on_start,
)

score = NumberVariable("score", initial=0)
player = Sprite(
    name="Player",
    costume=Costume(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
        '<circle cx="20" cy="20" r="16" fill="purple"/></svg>'
    ),
    scripts=(
        on_start(go_to(0, 0), score.reset()),
        on_key(Key.RIGHT, move_x(10)),
        on_key(Key.SPACE, score.add(1)),
    ),
)
game = Game("Small game", variables=(score,), sprites=(player,))
```

Use the same variable object in declarations and scripts. A different object with the same name is not a declared reference. Sprite names, variable names, and message names must be unique within their respective scopes.

## Add a project to the build

Define `game` in a module under `games/`, import it in `itchy/build.py`, and add it to `EXAMPLES`. The current player menu and development-server routes also need an entry for a newly selectable project; discovery is not automatic yet.

Keep growing projects organized by meaning:

```text
games/my_game/
  game.py
  player.py
  enemies.py
  assets/
tests/test_my_game.py
```

Use [named lists](sequences.md) for fixed sequences and typed `@action` functions when parameters change what is generated.
