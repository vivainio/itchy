# CLI reference

Run commands from the source checkout through uv:

```sh
uv run itchy --help
```

| Command | Effect |
| --- | --- |
| `itchy run` | Set up runtime, build examples, serve player, open browser |
| `itchy run --no-open` | Serve without opening a browser |
| `itchy run --port 4400` | Use another local port |
| `itchy setup` | Prepare local runtime tooling and synchronize dependencies |
| `itchy build` | Generate exports, preview ZIP, and Python distributions |
| `itchy check` | Run ty on the project |
| `itchy test` | Run pytest, including actual Scratch VM scenarios |
| `itchy test --preview` | Also build and verify the static preview |
| `itchy test --browser` | Also install Chromium and run Playwright checks |

`run` binds only to `127.0.0.1`. Ctrl+C stops it. Missing runtime packages are installed automatically; `setup` forces a lockfile-based dependency installation. 

The CLI is currently tied to the checkout's `games/`, `runner/`, and `web/` directories. Installing the generated core-library wheel alone is not enough to run the preview tooling. Use the checkout workflow above.
