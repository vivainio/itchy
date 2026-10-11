# API reference

All authoring names below are exported from `itchy.game`.

## Descriptions

| Type | Role |
| --- | --- |
| `Game(name, variables, sprites, messages=(), lists=(), extensions=(), stage=None)` | Project root |
| `Sprite(name, costume, scripts, x=0, y=0, sounds=(), costumes=(), procedures=())` | Sprite target |
| `Costume(svg, center_x=20, center_y=20)` | Inline SVG or image-file path |
| `Sound(name, source, rate=0, sample_count=0)` | Embedded WAV/MP3 |
| `Num(name, initial=0)` | Declared numeric variable and reporter |
| `Message(name)` | Declared broadcast reference |
| `Command` | Union of individual commands |
| `Steps` | Command or nested sequence of steps |
| `Condition` | Boolean reporter expression |
| `Number` | Numeric literal or reporter expression |

## Script and command builders

| Builder | Role |
| --- | --- |
| `events.on_start(*steps)` | Green-flag script |
| `events.on_click(*steps)` | Current sprite click event |
| `events.on_key(key, *steps)` | Key event script |
| `events.on_message(message, *steps)` | Broadcast receiver |
| `move.to(x, y)` | Set position |
| `move.x(distance)` | Change x position |
| `variable.set(value)` | Set variable |
| `variable.add(value)` | Change variable |
| `variable.reset()` | Restore declared initial value |
| `control.repeat(times, *steps)` | Literal or numeric-reporter count loop |
| `control.repeat_until(condition, *steps)` | Conditional loop |
| `control.forever(*steps)` | Unbounded loop |
| `if_(condition).then_(*steps).else_(*steps)` | Fluent conditional branches; else is optional |
| `control.if_then(condition, *steps)` | Conditional body |
| `control.if_else(condition, then=steps, otherwise=steps)` | Conditional branches |
| `control.wait(seconds)` | Wall-clock wait |
| `looks.hide()` / `looks.show()` | Current sprite visibility |
| `events.broadcast(message, wait=False)` | Send message |
| `sound.play(sound, wait=False)` | Play declared sound |
| `move.horizontal_controls(step=..., left=Key.LEFT, right=Key.RIGHT)` | Generate two key-event scripts |
| `@action` | Preserve types on a reusable block generator |

## Reporters and keys

Arithmetic: `+`, `-`, `*`, `/`. Comparisons: `<`, `>`, `<=`, `>=`, `.equals(...)`. Conditions compose using `&`, `|`, and `~`. Random numbers: `operators.random_number(low, high)`. Sensing: `sensing.key_down(Key...)` and `sensing.touching(sprite_or_name)`.

`Key` currently includes `LEFT`, `RIGHT`, `UP`, `DOWN`, `SPACE`, `ENTER`, `ANY`, `A`, `D`, `W`, and `S`.

See [Logic](logic.md) for Python evaluation pitfalls and [Assets](assets.md) for file formats. The native API below supports additional core blocks and extension opcodes. Extension behavior depends on the Scratch runtime and any required hardware or browser services.


## Motion, looks, sound, and sensing

- Motion: `move.steps(steps)`, `move.y(distance)`, `move.turn(degrees)` (negative turns left), `move.point_direction(direction)`, `move.set_x(x)`, `move.set_y(y)`, `move.glide(seconds, x, y)`, `move.bounce()`, `move.to_target(sprite_or_name)`, `move.point_towards(sprite_or_name)`, `move.rotation_style(style)`.
- Motion reporters: `move.x_position()`, `move.y_position()`, `move.direction()`.
- Looks: `looks.say(value, seconds=None)`, `looks.think(value, seconds=None)`, `looks.switch_costume(name)`, `looks.next_costume()`, `looks.set_size(size)`, `looks.change_size(amount)`, `looks.set_effect(effect, value)`, `looks.change_effect(effect, amount)`, `looks.clear_effects()`.
- Backdrops: `looks.switch_backdrop(name, wait=False)`, `looks.next_backdrop()`, `events.on_backdrop(name, *steps)`.
- Sound: `sound.stop_all()`, `sound.set_volume(value)`, `sound.change_volume(amount)`.
- Control: `control.wait_until(condition)`, `control.stop(option="all")`, `control.clone(sprite_or_name="_myself_")`, `control.delete_clone()`, `events.on_clone(*steps)`.
- Sensing: `sensing.ask(question)`, `sensing.answer()`, `sensing.mouse_x()`, `sensing.mouse_y()`, `sensing.mouse_down()`, `sensing.timer()`, `sensing.reset_timer()`.
- Operators: `operators.modulo(left, right)`, `operators.round_number(value)`, `operators.math_function(function, value)`.

Costumes retain the names `Default`, `Costume 2`, `Costume 3`, etc. To author stage scripts and backdrops, pass a `Sprite("Stage", ...)` as `Game.stage`. Its costumes, sounds, procedures, and scripts are compiled onto the actual stage target.

## Runtime strings and lists

Declare `String(name, initial="")` in `Game.variables`. Its `.set(value)` accepts text, numeric reporters, and string reporters; `.equals(value)` creates a condition. `operators.join(left, right, *parts)` (concatenates two or more values), `operators.letter(index, text)` (one-based), `operators.length(text)`, and `operators.contains(text, part)` run in Scratch.

Math reporters have named helpers: `abs_number`, `floor`, `ceil`, `sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `ln`, `log10`, `exp`, and `pow10`. Each takes one value. Trigonometric helpers use degrees, matching Scratch. `operators.math_op(operation, value)` remains available for generic operations.

Declare `ScratchList(name, initial=())` in `Game.lists`. Methods are `.append(value)`, `.delete(index)`, `.clear()`, `.insert(index, value)`, `.replace(index, value)`, `.item(index)`, `.length()`, `.index(value)`, and `.contains(value)`. Indices follow Scratch's one-based indexing and special index strings. Using the list itself as a native input reports its contents.

```python
from itchy import events, operators
words = ScratchList("words", ("hello",))
text = String("text")
script = events.on_start(words.append("world"), text.set(operators.join(words.item(1), "!")))
# Include words in Game.lists and text in Game.variables.
```

## Native My Blocks

Use `@procedure(warp=True)` to define a custom block with function-scoped parameters:

```python
from itchy import events
from itchy import move

@procedure(warp=True)
def walk(distance):
    return move.steps(distance)

player = Sprite("Player", costume, (events.on_start(walk(20)),), procedures=(walk,))
```

The compiler builds the function body once with argument reporters. Calls remain native Scratch custom-block calls. Bodies can call procedures declared later or call themselves recursively. Annotate Boolean parameters with `bool`. Parameters must be positional. Imports use original Scratch block and argument names, including their case, as Python function and parameter names where valid and unambiguous. They infer argument types and defaults from the function signature and regenerate argument IDs. Decorator options retain labels that require renamed parameters, custom `proccode` layouts, and defaults that cannot be represented by the signature.

`Procedure(name, arguments=(), body=(), warp=False)` defines a native Scratch custom block. Declare it in `Sprite.procedures`. Calling the procedure returns a command with checked argument count. Arguments belong to their procedure and cannot be used in unrelated scripts.

```python
from itchy import events
from itchy import move

distance = Argument("distance")
walk = Procedure("walk", (distance,), flatten((move.steps(distance),)), warp=True)
player = Sprite("Player", costume, (events.on_start(walk(20)),), procedures=(walk,))
```

Use `Argument(name, boolean=True)` for a Boolean argument, and pass it through a native Boolean input. `warp=True` enables Scratch's “run without screen refresh” mode. `@action` remains a build-time Python generator.

## General native blocks and extensions

`block(opcode, inputs={}, fields={}, substacks={})`, `reporter(opcode, inputs={}, fields={})`, and `predicate(opcode, inputs={}, fields={})` expose Scratch command, value, and Boolean blocks. `events.on_event(block(...), *steps)` exposes event hats. Use the exact opcode and input/field names defined by the runtime. These low-level builders do not validate opcode existence or each block's schema.

Inputs accept literals, variables, lists, argument references, existing expressions, native reporters, predicates, and `Menu(opcode, field, value)` dropdown shadows. Fields accept strings or declared variable/list references. Substacks accept command tuples produced by `flatten(...)`. The compiler maintains Scratch parent and next links and serializes native procedure mutations.

```python
from itchy import events
script = events.on_start(
    block("pen_clear"),
    block("pen_penDown"),
    block("motion_movesteps", inputs={"STEPS": 30}),
    block("pen_penUp"),
)
# Set Game.extensions=("pen",) to load the built-in pen extension.
```

Other runtime-provided extensions use the same API and declare their extension IDs in `Game.extensions`. The general API also exposes core blocks without a dedicated convenience builder, including layer order, sound effects, variable/list monitors, distance sensing, dates, and extension menus. Serialized extension IDs do not install third-party extension implementations.
