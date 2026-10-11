from itchy import move
from pathlib import Path
import subprocess
import sys


def test_ty_rejects_invalid_authored_game_types(tmp_path: Path) -> None:
    source = tmp_path / "invalid_game.py"
    source.write_text('''from itchy import control, events, move
from itchy.game import Key, Num, action
score = Num("score")
score.add("five")
events.on_key(123, move.x(10))
@action
def walk(distance: float):
    return move.x(distance)
walk("far")
move.x(score > 0)
control.if_then(score + 1, move.x(2))
control.if_(score + 1).then_(move.x(2))
events.on_start(control.if_(score > 0))
''')
    root = Path(__file__).resolve().parent.parent
    executable = Path(sys.executable).parent / "ty"
    result = subprocess.run(
        [str(executable), "check", "--project", str(root), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.count("invalid-argument-type") >= 7, result.stdout + result.stderr
