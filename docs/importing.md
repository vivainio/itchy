# Import and clean up a Scratch game

Start with a game you made in Scratch. You already know how it should behave, so its generated Python gives you a concrete way to learn itchy. Importing also lets you clean up a project that grew into a maze of scripts in the Scratch editor. An AI coding assistant can help you understand and refactor the source.

## Import your project

Save the project as an `.sb3` file from Scratch. Keep that original as a reference, then run:

```sh
uv tool install itchy
itchy import old-game.sb3 my-game
cd my-game
itchy run
```

`my-game` must be empty or not yet exist. Do not run `itchy init` first: importing creates the project configuration and source files for you. You can also run `itchy import /path/to/old-game.sb3` from an empty directory to import there.

## Find your scripts

The generated project follows Scratch's stage and sprite boundaries:

| File | What to look for |
| --- | --- |
| `game.py` | Assembly of the stage, sprites, shared declarations, and monitors |
| `stage.py` | Stage scripts, backdrops, and custom blocks |
| `sprite_*.py` | One sprite's scripts, costumes, sounds, and custom blocks |
| `vars.py` | Shared `Num` and `String` variables |
| `lists.py` | Shared Scratch lists |
| `messages.py` | Broadcast messages |
| `assets/` | Extracted costumes and sounds |
| `IMPORT_NOTES.md` | Unresolved custom block calls and generic or structural fallbacks |
| `itchy.toml` | Entry file and output directory |

Sprite-local variables live in `class svars` within their sprite module; local lists are declared there too. Scratch My Blocks become `@procedure` functions, with their parameters and warp settings retained. Familiar operations become itchy builders; other blocks may use the general `block`, `reporter`, or `predicate` API.

Read `IMPORT_NOTES.md` before editing. Generic builders can preserve blocks without a dedicated convenience function; unresolved calls and unusual source structures need closer inspection. Importing does not guarantee that every game's behavior is preserved. Run the game and compare its controls, scoring, costumes, sounds, and restart behavior with the original.

## Use AI to untangle the source

Commit the initial import to Git so you have a baseline. Ask an AI coding assistant to explain one sprite or script, then make small refactors you can review and play-test. Useful requests include:

- “Explain this sprite's scripts and the variables they share before changing anything.”
- “Rename unclear variables and update all declarations and references while preserving their scope.”
- “Extract these repeated commands into a named sequence. Preserve their order and event behavior.”
- “Group this sprite's initialization, movement, and scoring code so I can read it more easily.”
- “Check the import notes and explain which remaining generic blocks need attention.”

Tell the assistant to preserve gameplay unless you ask for a change. Scratch event scripts can run concurrently; changing broadcasts, waits, or script boundaries can change timing. Use ordinary named lists for reusable sequences, `@action` for generation-time helpers, and `@procedure` for native Scratch custom blocks. See [Named block sequences](sequences.md) and [Logic and expressions](logic.md).

Python type checking already catches many invalid itchy API calls, including wrong argument types and incomplete conditional builders. Use it alongside play-testing:

```sh
uv sync
uvx ty check
```

`uv sync` installs the project's itchy dependency into its local environment so the checker can resolve its typed API. `itchy import` and `itchy build` do not run the type checker automatically. Type checking checks the Python source; it does not prove that an exported Scratch archive is structurally valid or that gameplay is unchanged. Generic native builders also allow opcode strings that the type checker cannot validate.

After each change, run `itchy run` and repeat the same checks against the original. Review the source diff as well as the gameplay. AI can help with cleanup, but playing the game is how you check that the refactor still does what you intended.

## Export the cleaned-up game

```sh
itchy build
```

The build creates `dist/game.sb3`, `dist/preview/`, and `dist/itchy-preview.zip`. Load the `.sb3` in Scratch to inspect or edit the generated blocks, or share the browser preview. Keep the Python project on GitHub so future changes are easy to review.

Edits made later in Scratch do not automatically update the Python source. To bring a changed Scratch project back into itchy, save it as `.sb3` and import it into another empty directory, then compare the projects. See [Build and export](build.md) and [Sharing on GitHub](build.md#share-your-game-on-github).
