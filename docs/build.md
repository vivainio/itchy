# Build and export

```sh
itchy build
```

The command loads the game configured in `itchy.toml`, packages its assets, copies the browser runtime, and bundles audio support. In an itchy development checkout without project configuration, it builds the repository examples, book, and Python distributions. The following are generated under `dist/`:

| Output | Purpose |
| --- | --- |
| `*.sb3` | Native Scratch project exports |
| `manifest.json` | Project names and output paths |
| `preview/` | Static local player and embedded runtime files |
| `itchy-preview.zip` | Shareable local preview bundle |
| `../site/` | Built Zensical book |
| `packages/*.whl` | Python core-library wheel |
| `packages/*.tar.gz` | Python source distribution |

The preview includes Scratch VM, rendering, storage, bitmap conversion, audio, worker chunks, and third-party notices. Each `.sb3` separately contains its own costume and sound assets.

## Run the static bundle

Unzip `itchy-preview.zip`, then serve the extracted directory:

```sh
python3 -m http.server 4400 --bind 127.0.0.1
```

Open `http://127.0.0.1:4400/`. The built bundle includes its player runtime. Opening `index.html` directly as a local file is not supported because the player fetches its project files.

## Add examples and rebuild

Edit your project entry file (default `game.py`) and run `itchy build` again. Change `project.entry` and `project.output` in `itchy.toml` to customize the source and output paths.

The `.sb3` ZIP uses stable asset hashes, ordered entries, and fixed timestamps. Identical authored input produces identical project bytes. Python package and preview ZIP metadata are not promised to be byte-for-byte deterministic.

## Scratch compatibility

Exports use standard Scratch opcodes; projects can also declare supported runtime extensions. Website import is a separate account workflow and has not been automatically verified. Editing blocks in Scratch does not update the Python source.
