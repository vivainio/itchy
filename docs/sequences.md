# Named block sequences

A sequence can be an ordinary Python list. Give it a name that describes its purpose, then pass it directly to a script or control block.

```python
from itchy.game import Command, go_to, hide, if_, on_start

reset_player: list[Command] = [
    go_to(0, 0),
    score.reset(),
]

collect_coin: list[Command] = [
    score.add(1),
    hide(),
]

on_start(reset_player)
if_(touching(player)).then_(collect_coin)
```

The snippets assume the variables and sprite references from the enclosing game. There is no sequence-specific wrapper or syntax.

## Name both branches

```python
decide_turn = (
    if_(health > 0)
    .then_(move_right)
    .else_(reset_player)
)
```

Both branch bodies can be named Python lists. The underscore in `if_` and `else_` avoids Python keywords; `.then_(...)` makes the conditional command complete.

## Compose lists

```python
from itchy.game import Steps

prepare_round: list[Steps] = [
    reset_player,
    prepare_coin,
]

on_start(prepare_round, play_round)
```

`Command` is the union of individual command descriptions. `Steps` accepts a command or a nested Python sequence of steps. Use `list[Command]` for flat command lists and `list[Steps]` for lists containing other lists. The builders flatten nested sequences while preserving order.

Each use produces fresh Scratch block IDs. Reusing a list does not make the exported scripts share a block node. Builders capture their sequences when called: changing a list later does not change an already constructed script.

## Parameterized generators

Use a function when a sequence needs arguments:

```python
from itchy.game import action, move_x, repeat

@action
def walk(distance: float, count: int):
    return repeat(count, move_x(distance))

on_start(walk(4, 3), walk(-2, 2))
```

The decorator preserves argument types and normalizes the generated result into a command tuple. ty rejects `walk("far", 3)`. `@action` runs during generation and expands blocks inline; it does not create a Scratch custom-block definition.
