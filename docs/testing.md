# Testing

The CLI checks below are for developing itchy itself. Clone the repository, run `uv sync`, and activate `.venv` (`source .venv/bin/activate`) before running them.

```sh
itchy check
itchy test
itchy test --browser
```

## Typed VM scenarios

Python sends generated `.sb3` bytes and a scenario to a small JavaScript runner. The runner loads the actual Scratch VM, posts inputs, advances ticks, and returns snapshots.

```python
from games.coin_runner import game
from itchy.testing import Flag, Press, Release, Snapshot, Tick, simulate

states = simulate(
    game,
    Flag(), Tick(2),
    Press("ArrowRight"), Tick(2), Release("ArrowRight"),
    Snapshot(sprites=("Player",), variables=("score",)),
)
assert states[0]["sprites"]["Player"]["x"] == 10
```

`Press` and `Release` use browser keyboard names such as `ArrowRight` and a literal space. Authored `on_key` and `key_down` use the typed `Key` enum.

VM tests cover movement, restart, arithmetic, branching, key states, nested repeats, and repeat-until loops. Compiler tests validate declarations, assets, and build outputs. A negative typing fixture verifies that ty rejects invalid action arguments and conditions.

## Browser scenarios

Playwright checks actual keyboard input, rendering, PNG loading, WAV decoding, collision collection, hiding/showing, restart, and downloadable exports. The static mode uses the built preview instead of the development server:

```sh
itchy test --preview
```

This command builds the preview and prepares Chromium before testing.

## Limits

Headless scenarios have no renderer or audio engine. They cannot establish visual collision behavior or sound playback. Ticks advance the VM scheduler explicitly; they do not yet control Scratch timers or randomness. Scratch's private stepping API is isolated in `runner/runtime.js`; pinned package upgrades require rechecking it.

Automated browser checks establish asset decoding and state changes, not subjective sound quality or full website sharing compatibility.
