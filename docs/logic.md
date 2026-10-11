# Logic and expressions

Numeric expressions and conditions are separate types. ty rejects using `score > 0` as a movement distance or `score + 1` as an `if_then` condition.

```python
from itchy import control
from itchy.control import if_
from itchy import move


control.repeat_until(score >= 3, score.add(1))

decision = (
    if_(score.equals(3))
    .then_([move.x(score * 4), score.add(1)])
    .else_([score.reset()])
)
```

Branch bodies accept ordinary lists, nested lists, or individual commands. `if_(...).then_(...)` is a complete command without an else branch; `if_(...)` alone is an incomplete builder and ty rejects it in a script. The older `if_then` and `if_else` functions remain available.

## Numeric reporters

`Num` is a numeric expression. `+`, `-`, `*`, and `/` build arithmetic reporters, including reflected operations such as `10 - score`. `go_to`, `move_x`, `set`, and `add` accept numeric literals or expressions. `repeat` accepts a numeric literal or reporter count.

Comparisons `<`, `>`, `<=`, and `>=` generate conditions. Use `.equals(value)` for Scratch equality. Python `==` is object equality and does not generate a Scratch comparison.

## Boolean composition

```python
from itchy import control, sensing
from itchy.control import if_
if_(sensing.key_down(Key.SPACE) & (health > 0)).then_(award_points(1))
```

Use `&`, `|`, and `~` for AND, OR, and NOT. Parenthesize comparisons when composing them. Python `and`, `or`, `not`, `if`, and `while` evaluate at build time; conditions raise an error if coerced to a Python boolean. Avoid Python chained comparisons such as `0 < score < 10`; write `(score > 0) & (score < 10)`.

`operators.random_number(low, high)` generates a random numeric reporter evaluated at runtime. `control.wait(seconds)` yields for wall-clock time. These are not deterministic under the current headless tick adapter.

`sensing.key_down(Key.RIGHT)` generates a key-state reporter. `sensing.touching(sprite)` generates renderer-based collision sensing. A sprite name string, `_edge_`, or `_mouse_` is also accepted; ordinary sprite names are checked during compilation.

## Control sequences

| Builder | Scratch behavior |
| --- | --- |
| `if_(condition).then_(steps).else_(other_steps)` | Select a branch using the fluent API |
| `if_(condition).then_(steps)` | Run a single conditional branch |
| `control.if_then(condition, *steps)` | Run the body when true |
| `control.if_else(condition, then=steps, otherwise=steps)` | Select a branch |
| `control.repeat(count, *steps)` | Repeat a literal or reporter number of times |
| `control.repeat_until(condition, *steps)` | Repeat while the condition is false |
| `control.forever(*steps)` | Keep repeating until stopped |

## Order initialization with messages

Green-flag scripts run concurrently. Reset shared state before announcing that a round is ready:

```python
from itchy import events
from itchy import move

ready = Message("ready")

events.on_start(move.to(0, 0), score.reset(), events.broadcast(ready))
events.on_message(ready, prepare_coin, watch_for_player)
```

Declare `ready` in `Game.messages`. `events.broadcast(ready, wait=True)` waits for receiver scripts to complete; do not wait for a receiver that contains a `forever` loop.
