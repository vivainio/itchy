# Getting started

Install [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer, then install itchy:

```sh
uv tool install itchy
mkdir my-game
cd my-game
itchy init
itchy run
```

`itchy init` creates a starter project in an empty directory. The starter includes `game.py`, `assets/player.svg`, `itchy.toml`, and `pyproject.toml`. Comments in `game.py` link to guides in this book.

`itchy run` installs missing Scratch runtime dependencies in a user cache, compiles your game, and opens the player at `http://127.0.0.1:4317/`. The first run needs internet access. Automatic Bun setup supports macOS/Linux ARM64 and x64; install Bun manually on other platforms. No Scratch login is needed for local play.

## Create your game

Edit `game.py`. The starter uses arrow keys to move and Space to add a point. Refresh the browser after editing the game; Restart resets it. See [Game structure](game-structure.md), [Logic](logic.md), and the [API reference](api.md) to add behavior.

```sh
itchy run --port 4400 --no-open
```

Stop the server with Ctrl+C.

## Export to Scratch

Click **Download .sb3**, or run:

```sh
itchy build
```

The export is `dist/game.sb3`; `dist/preview/` and `dist/itchy-preview.zip` contain a browser player with its runtime. Open Scratch and select **File → Load from your computer** to import the `.sb3`. Website import has not been checked automatically.

## Share your game

Put your project on GitHub to share its Python source and assets. Other people can clone it, run `itchy run`, and fork it to make their own version. You can also share the `.sb3` and preview ZIP as GitHub release downloads. See [Sharing on GitHub](build.md#share-your-game-on-github).

## Upgrade

```sh
uv tool upgrade itchy
```

The source-checkout workflow is only needed for developing itchy itself; see [Testing](testing.md).
