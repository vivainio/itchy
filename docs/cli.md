# CLI reference

Install with `uv tool install itchy`, then run commands directly:

```sh
itchy --help
itchy init
itchy run
```

| Command | Effect |
| --- | --- |
| `itchy init [directory]` | Create a starter game in an empty directory (current directory by default) |
| `itchy import project.sb3 [directory]` | Translate a Scratch project into editable Python source |
| `itchy run` | Set up runtime, build your game, serve the player, open a browser |
| `itchy run --no-open` | Serve without opening a browser |
| `itchy run --port 4400` | Use another local port |
| `itchy setup` | Prepare cached runtime tooling and synchronize dependencies |
| `itchy build` | Generate `dist/game.sb3`, a browser preview, and a preview ZIP |
| `itchy check` | Run ty in an itchy development checkout |
| `itchy test` | Run pytest in an itchy development checkout |
| `itchy test --preview` | Also build and verify the checkout's static preview |
| `itchy test --browser` | Also install Chromium and run checkout browser checks |

`run` and `build` read `itchy.toml` in the current directory. `[project]` configures `entry` (default `game.py`) and `output` (default `dist`). The entry file must define a `Game` named `game`.

For a complete walkthrough, see [Import and clean up a Scratch game](importing.md).

`import` translates a Scratch `.sb3` archive into a small `game.py` assembly module with separate stage and sprite modules, copies costumes and sounds into `assets/`, and writes `IMPORT_NOTES.md` with unresolved custom blocks and source structures that still require generic fallback. Supported operations become purpose-built itchy expressions and commands for variables, lists, operators, control flow, motion, sensing, sound, costumes, and pen. Custom procedure definitions, arguments, warp settings, and calls become `@procedure` functions with local parameters. Sprite-local variables live in `class svars`; global variables live in `vars.py`. Run `itchy build` to compile the Python project back into a Scratch archive.

`run` binds only to `127.0.0.1`. Ctrl+C stops it. Missing runtime packages are installed automatically; `setup` forces a lockfile-based dependency installation. Runtime files live in the platform's user cache; set `ITCHY_CACHE_DIR` to override its location. The compiler, `init`, and `import` need no JavaScript runtime.

In an itchy development checkout without `itchy.toml`, `run` and `build` use the repository examples. The checkout build also creates documentation and Python distributions.
