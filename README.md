# itchy

Write typed Python games, generate native Scratch blocks, and export self-contained `.sb3` projects.

Install with [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer:

```sh
uv tool install itchy
mkdir my-game
cd my-game
itchy init
itchy run
```

`itchy init` creates a starter with two sprite modules, a stage, shared variable/list/message modules, SVG costumes, and project configuration in an empty directory. Edit the sprite modules to create your game; its comments link to the **[itchy book](https://vivainio.github.io/itchy/)**. `itchy run` prepares the Scratch runtime and opens your game in a local browser. The first run needs internet access to install runtime dependencies.

To translate a Scratch project into Python, run `itchy import my-game.sb3 [directory]`. This creates readable Python using itchy's purpose-built builders where available, copies costumes and sounds to `assets/`, and records unresolved source blocks and remaining generic fallbacks in `IMPORT_NOTES.md`. Custom blocks are reconstructed as Python `Procedure` objects. Run `itchy build` to export a new `.sb3` from the Python source.

```sh
itchy run --no-open       # Serve without opening a browser
itchy run --port 4400     # Choose a port
itchy build               # Export dist/game.sb3 and a shareable browser preview
```

Open an exported `.sb3` in Scratch with **File → Load from your computer**. Generated projects use standard Scratch blocks; Scratch website import is not yet automatically verified.

For development of itchy itself:

```sh
git clone https://github.com/vivainio/itchy.git
cd itchy
uv sync
source .venv/bin/activate
itchy check
itchy test --browser
```

The book's Markdown sources are in [`docs/`](docs/), with navigation and theme in [`zensical.toml`](zensical.toml).
