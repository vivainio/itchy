# Build and export

```sh
uv run itchy build
```

The command builds all entries in `itchy/build.py:EXAMPLES`, packages their assets, copies the browser runtime, bundles audio support, builds this book, and produces Python distributions. The following are generated under `dist/`:

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

The build currently uses an explicit example registry rather than arbitrary module discovery. Add a project to `EXAMPLES` and update menu/server routes as described in [Game structure](game-structure.md).

The `.sb3` ZIP uses stable asset hashes, ordered entries, and fixed timestamps. Identical authored input produces identical project bytes. Python package and preview ZIP metadata are not promised to be byte-for-byte deterministic.

## Scratch compatibility

Exports use standard Scratch opcodes and no custom extensions. Website import is a separate account workflow and has not been automatically verified. Editing blocks in Scratch does not update the Python source.
