# Getting started

## Install the checkout

Install [uv](https://docs.astral.sh/uv/) and use Python 3.12 or newer. uv can provision a compatible Python interpreter.

```sh
git clone https://github.com/vivainio/itchy.git
cd itchy
uv sync
uv run itchy run
```

`itchy run` prepares its JavaScript tooling locally, installs missing runtime dependencies from the lockfile, compiles the projects, and serves the player at `http://127.0.0.1:4317/`. Automatic setup supports macOS/Linux ARM64 and x64. The first setup needs internet access; see [Architecture](architecture.md) for runtime details.

The browser runs the Scratch VM, renderer, bitmap adapter, storage, and audio engine. No Scratch login is needed for local play.

## Play the examples

Select a game from the player menu. The movement sandbox uses arrows to move and Space to increment score. The coin-collection example uses arrows to reach the coin; collection increments the score once, hides the coin, and plays a sound. Restart resets the selected game.

To use a different port or avoid opening a browser:

```sh
uv run itchy run --port 4400 --no-open
```

Refresh after editing a game module. Stop the server with Ctrl+C.

## Export to Scratch

Click **Download .sb3**, or run:

```sh
uv run itchy build
```

Open the Scratch editor and select **File → Load from your computer**. Import an exported `.sb3`, then save/share using your own Scratch account. The generated projects use standard Scratch blocks; website import has not yet been checked automatically.

## Check your changes

```sh
uv run itchy check
uv run itchy test
uv run itchy test --browser
```

The browser test command installs Chromium if needed. See [Testing](testing.md) for scenarios and practical limits.
