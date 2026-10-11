from pathlib import Path
from games.coin_runner import game
from itchy.compiler import compile_game


def main() -> None:
    path = Path("dist/coin-runner.sb3")
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(compile_game(game))
    print(f"Exported {path}")


if __name__ == "__main__":
    main()
