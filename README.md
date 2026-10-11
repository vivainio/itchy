# itchy

Write typed Python games, generate native Scratch blocks, and export self-contained `.sb3` projects.

**[Read the itchy book](https://vivainio.github.io/itchy/)** for authoring, named Python lists, logic, assets, Scratch recreations, testing, and CLI reference.

```sh
git clone https://github.com/vivainio/itchy.git
cd itchy
uv sync
uv run itchy run
```

`itchy run` sets up the local runtime, builds the examples, starts the player, and opens your browser. This early prototype currently runs from a source checkout; it has not been published to PyPI.

```sh
uv run itchy build           # .sb3 exports, offline preview, book, Python packages
uv run itchy check           # ty
uv run itchy test --browser  # Python/VM and browser tests
uv run zensical serve        # preview the book
```

The book's Markdown sources are in [`docs/`](docs/), with navigation and theme in [`zensical.toml`](zensical.toml). Generated projects use standard Scratch blocks; Scratch website import is not yet automatically verified.
