from pathlib import Path
import subprocess
import sys


def test_ty_rejects_invalid_authored_game_types(tmp_path: Path) -> None:
    source = tmp_path / "invalid_game.py"
    source.write_text('''from itchy.game import Key, NumberVariable, action, move_x, on_key, if_then, if_, on_start
score = NumberVariable("score")
score.add("five")
on_key("right", move_x(10))
@action
def walk(distance: float):
    return move_x(distance)
walk("far")
move_x(score > 0)
if_then(score + 1, move_x(2))
if_(score + 1).then(move_x(2))
on_start(if_(score > 0))
''')
    root = Path(__file__).resolve().parent.parent
    executable = Path(sys.executable).parent / "ty"
    result = subprocess.run(
        [str(executable), "check", "--project", str(root), str(source)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert result.stdout.count("invalid-argument-type") >= 7, result.stdout + result.stderr
