# The itchy book

itchy lets you describe games in typed Python, compile those descriptions into Scratch blocks, and export ordinary `.sb3` projects. The exported games contain their costumes and sounds and remain editable in Scratch.

```sh
uv tool install itchy
mkdir my-game
cd my-game
itchy init
itchy run
```

That command prepares the local JavaScript runtime, builds your game, starts a player, and opens your browser. Start with [Getting started](getting-started.md).

## Write sequences you can read

```python
collect_coin: list[Command] = [
    score.add(1),
    collected.set(1),
    play_sound(collect_sound),
    hide(),
]

watch_for_player = forever(
    if_(collected.equals(0) & touching(player)).then_(collect_coin),
)
```

These are Python values describing runtime behavior. Scratch executes the generated blocks. [Named block sequences](sequences.md) explains how to compose ordinary lists; [Logic and expressions](logic.md) covers conditions and reporters.

## Share your games on GitHub

An itchy game is a Python project you can share on GitHub. Commit your game code, costumes, sounds, and configuration so other people can clone it and play with `itchy run`. They can also fork the project, change the game, and contribute improvements through pull requests. Git records the history of your game, and readable Python makes changes easy to review.

For people who just want to play, attach the exported `.sb3` and browser preview ZIP to a GitHub release. See [Sharing on GitHub](build.md#share-your-game-on-github) for the workflow.

## Learn through examples

The repository includes a movement/scoring sandbox and a collectible game with a PNG costume, WAV sound, collision detection, and message-ordered initialization. [Scratch recreations](scratch-examples.md) relates publicly shared Scratch projects to readable Python implementations, documenting which behavior is translated and which is adapted.

## Current scope

Install itchy as a tool and use `itchy init` to create a project. The CLI loads the `game` declared in your project entry file. `itchy import project.sb3` reconstructs Python modules, assets, and import notes from a Scratch project. `@action` expands ordinary blocks rather than producing native Scratch “My Blocks” definitions. Python installation and generation are separate from the JavaScript runtime used for testing and preview.

The [API reference](api.md) lists supported operations. The [testing guide](testing.md) distinguishes headless VM tests from browser tests. See [Getting started](getting-started.md) for installation.
