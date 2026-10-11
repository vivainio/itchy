# itchy

Write readable, typed Python game scripts. Generate standard Scratch blocks and export `.sb3` projects that remain editable in Scratch.

```python
from itchy.game import (
    Game, Key, NumberVariable, Sprite, action, go_to,
    horizontal_controls, on_key, on_start,
)

score = NumberVariable("score", initial=0)

@action
def collect(points: float):
    return score.add(points)

game = Game(
    name="Coin Runner",
    variables=(score,),
    sprites=(Sprite(
        name="Player",
        costume=player_costume,
        scripts=(
            on_start(go_to(0, 0), score.reset()),
            *horizontal_controls(step=10),
            on_key(Key.SPACE, collect(1)),
        ),
    ),),
)
```

See the complete runnable example in [`games/coin_runner.py`](games/coin_runner.py).

## Run locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and [Bun](https://bun.sh). Bun runs only the Scratch VM and browser test bridge; Python authors and compiles the games.

```sh
uv sync
bun install --frozen-lockfile
uv run ty check
uv run pytest
uv run python -m itchy.build       # dist/coin-runner.sb3
uv run python -m itchy.server      # http://127.0.0.1:4317
bun x playwright install chromium # first browser-test setup
bun run test:browser               # starts its own server
```

On the original development Mac, `./bunw` also works with the project-local Bun binary. On other machines it uses your installed Bun.

The preview demo moves in 10-unit steps using arrow keys. Space increments score. Restart resets score and position. Refresh after editing the example. Download the `.sb3`, then use **File → Load from your computer** in Scratch. Import on scratch.mit.edu has not yet been verified; publishing there requires your Scratch account.

## Structure

- `itchy/game.py`: frozen typed descriptions, event builders, and reusable generators.
- `itchy/compiler.py`: standard Scratch block graphs, assets, deterministic `.sb3` ZIPs.
- `games/coin_runner.py`: authored Python game.
- `itchy/testing.py`: typed Python scenarios sent through JSON to the Scratch VM.
- `tests/`: behavioral, packaging, and type-checker tests.
- `runner/`: small JavaScript Scratch VM and Playwright adapters.
- `web/index.html`: local player and export download.

`@action` functions run at build time and generate ordinary block sequences. They preserve parameter types. They do not yet emit Scratch “My Blocks” definitions. Nested `repeat(3, move_x(10), score.add(1))` becomes a real Scratch repeat block. No Python code is embedded in the export.

Supported operations: green-flag and key events, positioning, horizontal movement, numeric variable set/change, and nested repeat. Costumes are SVGs with explicit rotation centers. Variables must be declared in the game; the compiler verifies references. **ty** checks authored Python, including action arguments and enum keys.

Next extensions can add typed expressions, conditions, continuous controls, collisions, broadcasts, sprite-local variables, and higher-level platformer/collectible behaviors. Larger games can keep sprites, assets, and scenario files separately.

## Tests

Python tests generate `.sb3` bytes, send them to the real Scratch VM, simulate inputs and explicit ticks, and inspect state. Browser tests check rendering, real keyboard input, reset, and export download. Private VM stepping APIs are isolated in `runner/runtime.js`, and Scratch packages are pinned. Timed waits and randomness are not yet controlled; collision and appearance checks need the browser renderer. Headless renderer warnings are expected.

This is an early prototype. Scratch editor changes are not imported back into Python. The preview and VM test tooling run from this repository; the package's core compiler itself uses only Python's standard library. Nothing has been uploaded to PyPI.
