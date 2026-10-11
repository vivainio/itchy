# API reference

All authoring names below are exported from `itchy.game`.

## Descriptions

| Type | Role |
| --- | --- |
| `Game(name, variables, sprites, messages=(), lists=(), extensions=(), stage=None)` | Project root |
| `Sprite(name, costume, scripts, x=0, y=0, sounds=(), costumes=(), procedures=())` | Sprite target |
| `Costume(svg, center_x=20, center_y=20)` | Inline SVG or image-file path |
| `Sound(name, source, rate=0, sample_count=0)` | Embedded WAV/MP3 |
| `NumberVariable(name, initial=0)` | Declared numeric variable and reporter |
| `Message(name)` | Declared broadcast reference |
| `Command` | Union of individual commands |
| `Steps` | Command or nested sequence of steps |
| `Condition` | Boolean reporter expression |
| `Number` | Numeric literal or reporter expression |

## Script and command builders

| Builder | Role |
| --- | --- |
| `on_start(*steps)` | Green-flag script |
| `on_click(*steps)` | Current sprite click event |
| `on_key(key, *steps)` | Key event script |
| `on_message(message, *steps)` | Broadcast receiver |
| `go_to(x, y)` | Set position |
| `move_x(distance)` | Change x position |
| `variable.set(value)` | Set variable |
| `variable.add(value)` | Change variable |
| `variable.reset()` | Restore declared initial value |
| `repeat(times, *steps)` | Literal or numeric-reporter count loop |
| `repeat_until(condition, *steps)` | Conditional loop |
| `forever(*steps)` | Unbounded loop |
| `if_(condition).then(*steps).else_(*steps)` | Fluent conditional branches; else is optional |
| `if_then(condition, *steps)` | Conditional body |
| `if_else(condition, then=steps, otherwise=steps)` | Conditional branches |
| `wait(seconds)` | Wall-clock wait |
| `hide()` / `show()` | Current sprite visibility |
| `broadcast(message, wait=False)` | Send message |
| `play_sound(sound, wait=False)` | Play declared sound |
| `horizontal_controls(step=..., left=Key.LEFT, right=Key.RIGHT)` | Generate two key-event scripts |
| `@action` | Preserve types on a reusable block generator |

## Reporters and keys

Arithmetic: `+`, `-`, `*`, `/`. Comparisons: `<`, `>`, `<=`, `>=`, `.equals(...)`. Conditions compose using `&`, `|`, and `~`. Random numbers: `random_number(low, high)`. Sensing: `key_down(Key...)` and `touching(sprite_or_name)`.

`Key` currently includes `LEFT`, `RIGHT`, `UP`, `DOWN`, `SPACE`, `ENTER`, `ANY`, `A`, `D`, `W`, and `S`.

See [Logic](logic.md) for Python evaluation pitfalls and [Assets](assets.md) for file formats. The native API below supports additional core blocks and extension opcodes. Extension behavior depends on the Scratch runtime and any required hardware or browser services.


## Motion, looks, sound, and sensing

- Motion: `move(steps)`, `move_y(distance)`, `turn(degrees)` (negative turns left), `point_direction(direction)`, `set_x(x)`, `set_y(y)`, `glide(seconds, x, y)`, `bounce()`, `go_to_target(sprite_or_name)`, `point_towards(sprite_or_name)`, `rotation_style(style)`.
- Motion reporters: `x_position()`, `y_position()`, `direction()`.
- Looks: `say(value, seconds=None)`, `think(value, seconds=None)`, `switch_costume(name)`, `next_costume()`, `set_size(size)`, `change_size(amount)`, `set_effect(effect, value)`, `change_effect(effect, amount)`, `clear_effects()`.
- Backdrops: `switch_backdrop(name, wait=False)`, `next_backdrop()`, `on_backdrop(name, *steps)`.
- Sound: `stop_sounds()`, `set_volume(value)`, `change_volume(amount)`.
- Control: `wait_until(condition)`, `stop(option="all")`, `clone(sprite_or_name="_myself_")`, `delete_clone()`, `on_clone(*steps)`.
- Sensing: `ask(question)`, `answer()`, `mouse_x()`, `mouse_y()`, `mouse_down()`, `timer()`, `reset_timer()`.
- Operators: `modulo(left, right)`, `round_number(value)`, `math_function(function, value)`.

Costumes retain the names `Default`, `Costume 2`, `Costume 3`, etc. To author stage scripts and backdrops, pass a `Sprite("Stage", ...)` as `Game.stage`. Its costumes, sounds, procedures, and scripts are compiled onto the actual stage target.

## Runtime strings and lists

Declare `StringVariable(name, initial="")` in `Game.variables`. Its `.set(value)` accepts text, numeric reporters, and string reporters; `.equals(value)` creates a condition. `join(left, right)`, `letter(index, text)` (one-based), `length(text)`, and `contains(text, part)` run in Scratch.

Declare `ScratchList(name, initial=())` in `Game.lists`. Methods are `.append(value)`, `.delete(index)`, `.clear()`, `.insert(index, value)`, `.replace(index, value)`, `.item(index)`, `.length()`, `.index(value)`, and `.contains(value)`. Indices follow Scratch's one-based indexing and special index strings. Using the list itself as a native input reports its contents.

```python
words = ScratchList("words", ("hello",))
text = StringVariable("text")
script = on_start(words.append("world"), text.set(join(words.item(1), "!")))
# Include words in Game.lists and text in Game.variables.
```

## Native My Blocks

`Procedure(name, arguments=(), body=(), warp=False)` defines a native Scratch custom block. Declare it in `Sprite.procedures`. Calling the procedure returns a command with checked argument count. Arguments belong to their procedure and cannot be used in unrelated scripts.

```python
distance = Argument("distance")
walk = Procedure("walk", (distance,), flatten((move(distance),)), warp=True)
player = Sprite("Player", costume, (on_start(walk(20)),), procedures=(walk,))
```

Use `Argument(name, boolean=True)` for a Boolean argument, and pass it through a native Boolean input. `warp=True` enables Scratch's “run without screen refresh” mode. `@action` remains a build-time Python generator.

## General native blocks and extensions

`block(opcode, inputs={}, fields={}, substacks={})`, `reporter(opcode, inputs={}, fields={})`, and `predicate(opcode, inputs={}, fields={})` expose Scratch command, value, and Boolean blocks. `on_event(block(...), *steps)` exposes event hats. Use the exact opcode and input/field names defined by the runtime. These low-level builders do not validate opcode existence or each block's schema.

Inputs accept literals, variables, lists, argument references, existing expressions, native reporters, predicates, and `Menu(opcode, field, value)` dropdown shadows. Fields accept strings or declared variable/list references. Substacks accept command tuples produced by `flatten(...)`. The compiler maintains Scratch parent and next links and serializes native procedure mutations.

```python
script = on_start(
    block("pen_clear"),
    block("pen_penDown"),
    block("motion_movesteps", inputs={"STEPS": 30}),
    block("pen_penUp"),
)
# Set Game.extensions=("pen",) to load the built-in pen extension.
```

Other runtime-provided extensions use the same API and declare their extension IDs in `Game.extensions`. The general API also exposes core blocks without a dedicated convenience builder, including layer order, sound effects, variable/list monitors, distance sensing, dates, and extension menus. Serialized extension IDs do not install third-party extension implementations.
