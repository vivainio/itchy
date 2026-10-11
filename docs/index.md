# The itchy book

itchy lets you describe games in typed Python, compile those descriptions into Scratch blocks, and export ordinary `.sb3` projects. The exported games contain their costumes and sounds and remain editable in Scratch.

```sh
uv run itchy run
```

That command prepares the local JavaScript runtime, builds the example projects, starts a player, and opens your browser. Start with [Getting started](getting-started.md).

## Write sequences you can read

```python
collect_coin: list[Command] = [
    score.add(1),
    collected.set(1),
    play_sound(collect_sound),
    hide(),
]

watch_for_player = forever(
    if_then(collected.equals(0) & touching(player), collect_coin),
)
```

These are Python values describing runtime behavior. Scratch executes the generated blocks. [Named block sequences](sequences.md) explains how to compose ordinary lists; [Logic and expressions](logic.md) covers conditions and reporters.

## Learn through examples

The repository includes a movement/scoring sandbox and a collectible game with a PNG costume, WAV sound, collision detection, and message-ordered initialization. [Scratch recreations](scratch-examples.md) relates publicly shared Scratch projects to readable Python implementations, documenting which behavior is translated and which is adapted.

## Current scope

This is an early source-checkout tool. The CLI builds the repository's registered examples; it does not yet discover arbitrary game modules. There is no general Scratch-to-Python importer. `@action` expands ordinary blocks rather than producing native Scratch “My Blocks” definitions. Python installation and generation are separate from the JavaScript runtime used for testing and preview.

The [API reference](api.md) lists supported operations. The [testing guide](testing.md) distinguishes headless VM tests from browser tests. No PyPI release has been published.
