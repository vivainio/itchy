"""Starter projects and loading authored games without a source checkout."""
from contextlib import contextmanager
from collections.abc import Generator
from html import escape
import os
from pathlib import Path
import runpy
import sys
import tomllib

from itchy.game import Game

BOOK = "https://vivainio.github.io/itchy/"
STARTER = '''"""My first itchy game. Read the book: https://vivainio.github.io/itchy/"""
from pathlib import Path

from itchy.game import (
    Costume, Game, Key, NumberVariable, Sprite,
    go_to, horizontal_controls, on_key, on_start,
)

# Describe sprites and scripts: https://vivainio.github.io/itchy/game-structure/
score = NumberVariable("score")
# Add costumes and sounds: https://vivainio.github.io/itchy/assets/
assets = Path(__file__).parent / "assets"
player = Costume(assets / "player.svg")

# Commands describe Scratch blocks; they run when their event fires.
# Controls and conditions: https://vivainio.github.io/itchy/logic/
# All available builders: https://vivainio.github.io/itchy/api/
game = Game(
    name="My first game",
    variables=(score,),
    sprites=(Sprite("Player", player, (
        on_start(go_to(0, 0), score.reset()),
        *horizontal_controls(step=10),
        on_key(Key.SPACE, score.add(1)),
    )),),
)
'''


def init_project(directory: Path) -> None:
    directory = directory.expanduser().resolve()
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"{directory} must be an empty directory; no files were changed")
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "game.py": STARTER,
        "itchy.toml": '[project]\nentry = "game.py"\noutput = "dist"\n',
        "pyproject.toml": '[project]\nname = "my-itchy-game"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = ["itchy>=0.1.0"]\n',
        ".gitignore": "dist/\n.venv/\n__pycache__/\n",
        "README.md": f"# My itchy game\n\nRun `itchy run` to play. Edit `game.py` and restart to see changes.\nRun `itchy build` to export `dist/game.sb3` and a browser preview.\n\n[Learn to create games in the itchy book]({BOOK}).\n",
        "assets/player.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect x="2" y="2" width="36" height="36" rx="8" fill="#8b5cf6"/></svg>\n',
    }
    for name, content in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(f"Created itchy project in {directory}\nRun itchy run from that directory.\nBook: {BOOK}")


def project_config(directory: Path) -> tuple[Path, Path]:
    directory = directory.resolve()
    config = directory / "itchy.toml"
    if not config.is_file():
        raise FileNotFoundError(f"No itchy.toml in {directory}. Run itchy init in an empty directory first.")
    settings = tomllib.loads(config.read_text()).get("project", {})
    entry = settings.get("entry", "game.py")
    output = settings.get("output", "dist")
    if not isinstance(entry, str) or not isinstance(output, str):
        raise ValueError("project.entry and project.output must be paths expressed as strings")
    return directory / entry, directory / output


@contextmanager
def project_context(directory: Path) -> Generator[None]:
    previous = Path.cwd()
    previous_path = sys.path.copy()
    os.chdir(directory)
    sys.path.insert(0, str(directory))
    try:
        yield
    finally:
        os.chdir(previous)
        sys.path[:] = previous_path


def load_game(directory: Path) -> Game:
    directory = directory.resolve()
    entry, _ = project_config(directory)
    with project_context(directory):
        namespace = runpy.run_path(str(entry))
    game = namespace.get("game")
    if not isinstance(game, Game):
        raise ValueError(f"{entry} must define a Game named game")
    return game


def preview_html(template: str, game: Game) -> str:
    template = template.replace("Scratch local playground", escape(game.name))
    start = template.index('<p><label>Game ')
    end = template.index('</p>', start) + len('</p>')
    template = template[:start] + '<select id="game" hidden><option value="/game.sb3">Game</option></select>' + template[end:]
    # Relative links let the preview be hosted under any URL prefix.
    return template.replace('"/vendor/', '"vendor/').replace('"/game.sb3"', '"game.sb3"').replace("'/game.sb3'", "'game.sb3'")
