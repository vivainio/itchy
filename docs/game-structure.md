# Game structure

A `Game` contains declared variables, sprites, and optional messages. Each sprite contains costumes, sounds, and event scripts. Frozen dataclasses keep the authored description separate from execution state.

```python
from pathlib import Path

from itchy.game import (
    Costume, Game, Key, NumberVariable, Sprite,
    go_to, move_x, on_key, on_start,
)

assets = Path(__file__).parent / "assets"
score = NumberVariable("score", initial=0)
player = Sprite(
    name="Player",
    costume=Costume(assets / "player.svg"),
    scripts=(
        on_start(go_to(0, 0), score.reset()),
        on_key(Key.RIGHT, move_x(10)),
        on_key(Key.SPACE, score.add(1)),
    ),
)
game = Game("Small game", variables=(score,), sprites=(player,))
```

The bundled samples load every sprite image from `games/assets/`. Keep image content in files and use paths relative to the game module so launching from another directory does not change asset resolution.

Use the same variable object in declarations and scripts. A different object with the same name is not a declared reference. Sprite names, variable names, and message names must be unique within their respective scopes.

## Add a project to the build

Define `game` in your project entry file (`game.py` by default). `itchy run` and `itchy build` load that file using `itchy.toml`. No registration in itchy itself is needed.

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
