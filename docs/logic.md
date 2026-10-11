# Logic and expressions

Numeric expressions and conditions are separate types. ty rejects using `score > 0` as a movement distance or `score + 1` as an `if_then` condition.

```python
from itchy.game import if_else, if_then, repeat_until

repeat_until(score >= 3, score.add(1))

if_else(
    score.equals(3),
    then=[move_x(score * 4), score.add(1)],
    otherwise=score.reset(),
)
```

## Numeric reporters

`NumberVariable` is a numeric expression. `+`, `-`, `*`, and `/` build arithmetic reporters, including reflected operations such as `10 - score`. `go_to`, `move_x`, `set`, and `add` accept numeric literals or expressions. `repeat` currently takes a literal integer count.

Comparisons `<`, `>`, `<=`, and `>=` generate conditions. Use `.equals(value)` for Scratch equality. Python `==` is object equality and does not generate a Scratch comparison.

## Boolean composition

```python
if_then(
    key_down(Key.SPACE) & (health > 0),
    award_points(1),
)
```

Use `&`, `|`, and `~` for AND, OR, and NOT. Parenthesize comparisons when composing them. Python `and`, `or`, `not`, `if`, and `while` evaluate at build time; conditions raise an error if coerced to a Python boolean. Avoid Python chained comparisons such as `0 < score < 10`; write `(score > 0) & (score < 10)`.

`random_number(low, high)` generates a random numeric reporter evaluated at runtime. `wait(seconds)` yields for wall-clock time. These are not deterministic under the current headless tick adapter.

`key_down(Key.RIGHT)` generates a key-state reporter. `touching(sprite)` generates renderer-based collision sensing. A sprite name string, `_edge_`, or `_mouse_` is also accepted; ordinary sprite names are checked during compilation.

## Control sequences

| Builder | Scratch behavior |
| --- | --- |
| `if_then(condition, *steps)` | Run the body when true |
| `if_else(condition, then=steps, otherwise=steps)` | Select a branch |
| `repeat(count, *steps)` | Repeat a literal number of times |
| `repeat_until(condition, *steps)` | Repeat while the condition is false |
| `forever(*steps)` | Keep repeating until stopped |

## Order initialization with messages

Green-flag scripts run concurrently. Reset shared state before announcing that a round is ready:

```python
ready = Message("ready")

on_start(go_to(0, 0), score.reset(), broadcast(ready))
on_message(ready, prepare_coin, watch_for_player)
```

Declare `ready` in `Game.messages`. `broadcast(ready, wait=True)` waits for receiver scripts to complete; do not wait for a receiver that contains a `forever` loop.
