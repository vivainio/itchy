# Game structure

A `Game` contains declared variables, sprites, and optional messages. Each sprite contains costumes, sounds, and event scripts. Frozen dataclasses keep the authored description separate from execution state.

```python
from itchy import events
from itchy import move

from pathlib import Path

from itchy.game import Costume, Game, Key, Num, Sprite

assets = Path(__file__).parent / "assets"
score = Num("score", initial=0)
player = Sprite(
    name="Player",
    costume=Costume(assets / "player.svg"),
    scripts=(
        events.on_start(move.to(0, 0), score.reset()),
        events.on_key(Key.RIGHT, move.x(10)),
        events.on_key(Key.SPACE, score.add(1)),
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

## Starter and imported projects

`itchy init` uses the importer's module layout: `game.py` assembles `stage.py` and two `sprite_*.py` modules. Shared declarations live in `vars.py`, `lists.py`, and `messages.py`; sprite-local variables live in a `svars` class inside their sprite module.

The starter discovers shared declarations with reflection:

```python
import vars
from itchy.game import Num, String

variables = tuple(value for value in vars.__dict__.values()
                  if isinstance(value, (Num, String)))
```

Pass that tuple as `Game.variables`. The starter applies the same pattern to `ScratchList` and `Message`. Add each declaration once in its module; helper values and imported classes are excluded by the type filter. Use one module name per declaration to avoid discovering aliases twice. Sprite-local declarations remain in `Sprite.variables`.
