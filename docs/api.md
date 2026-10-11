# API reference

All authoring names below are exported from `itchy.game`.

## Descriptions

| Type | Role |
| --- | --- |
| `Game(name, variables, sprites, messages=())` | Project root |
| `Sprite(name, costume, scripts, x=0, y=0, sounds=(), costumes=())` | Sprite target |
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
| `repeat(times, *steps)` | Fixed-count loop |
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

See [Logic](logic.md) for Python evaluation pitfalls and [Assets](assets.md) for file formats. Motion beyond `go_to` and `move_x`, arbitrary Scratch extensions, native custom-block definitions, clones, and costume switching are not part of this initial API.
