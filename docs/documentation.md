# Documentation

The book uses [Zensical](https://zensical.org/), with the same pinned version, theme features, light/dark palettes, code highlighting, and publishing pattern as the roto book.

```sh
uv sync
uv run zensical serve
uv run zensical build --clean --strict
```

The build produces `site/`. Generated output and caches are ignored by Git. Markdown chapters live in `docs/`; navigation and theme settings live in `zensical.toml`.

## Maintain examples

Prefer runnable source files over copied snippets. Zensical's snippets extension can include repository files:

````markdown
```python
--8<-- "games/logic_playground.py"
```
````

Keep API claims aligned with checked source and tests. Mark adaptations, missing behavior, and planned features explicitly. Link original Scratch projects and preserve attribution when describing recreations.

## GitHub Pages

The Documentation workflow validates pull requests and publishes pushes to `main`. Only the deployment job receives Pages and identity-token write permissions. In repository **Settings → Pages**, select **GitHub Actions** as the build source before the first deployment.

The configured public address is [the itchy book](https://vivainio.github.io/itchy/). Publication runs through GitHub Actions after a push to `main`.
