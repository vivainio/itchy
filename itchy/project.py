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
from itchy.game import Game, Message, Monitor, Num, ScratchList, String
import vars
import lists
import messages
from stage import _stage
from sprite_player import player
from sprite_coin import coin

# Discover shared declarations as you add them to their modules.
# All available builders: https://vivainio.github.io/itchy/api/
game = Game(
    name="My first game",
    variables=tuple(value for value in vars.__dict__.values()
                    if isinstance(value, (Num, String))),
    lists=tuple(value for value in lists.__dict__.values() if isinstance(value, ScratchList)),
    messages=tuple(value for value in messages.__dict__.values() if isinstance(value, Message)),
    stage=_stage,
    sprites=(player, coin),
    monitors=(Monitor(vars.score, x=10, y=10, visible=True),),
)
'''

STARTER_MODULES = {
    "vars.py": '''"""Shared variables, available to every sprite."""
from itchy.game import Num, String

score = Num("score")
status = String("status", "Click the coin!")
''',
    "lists.py": '''"""Shared Scratch lists."""
from itchy.game import ScratchList

collected = ScratchList("collected")
''',
    "messages.py": '''"""Broadcasts coordinate initialization and sprite scripts."""
from itchy.game import Message

ready = Message("ready")
''',
    "stage.py": '''"""Reset shared state before starting the sprites."""
from itchy import events
from itchy import move
from itchy.game import Costume, Sprite
import vars
import lists
import messages

_stage = Sprite("Stage", Costume('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><rect width="480" height="360" fill="#f1f5f9"/></svg>'), (
    events.on_start(vars.score.reset(), vars.status.set(vars.status.initial), lists.collected.clear(),
             events.broadcast(messages.ready)),
))
''',
    "sprite_player.py": '''"""Move with the arrow keys. Local variables live in svars."""
from itchy import events
from pathlib import Path
from itchy import move
from itchy.game import Costume, Key, Num, Sprite
import messages

_root = Path(__file__).parent


class svars:
    step = Num("step", 10)


player = Sprite("Player", Costume(_root / "assets/player.svg"), (
    events.on_message(messages.ready, svars.step.reset(), move.to(-80, 0)),
    events.on_key(Key.RIGHT, move.x(svars.step)),
    events.on_key(Key.LEFT, move.x(0 - svars.step)),
), variables=(svars.step,))
''',
    "sprite_coin.py": '''"""Click the coin to score and record each collection in a list."""
from itchy import events, looks, operators
from pathlib import Path
from itchy import move
from itchy.game import Costume, Sprite
import vars
import lists
import messages

_root = Path(__file__).parent

coin = Sprite("Coin", Costume(_root / "assets/coin.svg"), (
    events.on_message(messages.ready, move.to(80, 0), looks.show()),
    events.on_click(vars.score.add(1), lists.collected.append(vars.score),
             vars.status.set("Coin collected!"), looks.say(vars.status, seconds=0.5),
             move.to(operators.random_number(-200, 200), operators.random_number(-140, 140))),
))
''',
}


def init_project(directory: Path) -> None:
    directory = directory.expanduser().resolve()
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"{directory} must be an empty directory; no files were changed")
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "game.py": STARTER,
        **STARTER_MODULES,
        "itchy.toml": '[project]\nentry = "game.py"\noutput = "dist"\n',
        "pyproject.toml": '[project]\nname = "my-itchy-game"\nversion = "0.1.0"\nrequires-python = ">=3.12"\ndependencies = ["itchy>=0.1.2"]\n',
        ".gitignore": "dist/\n.venv/\n__pycache__/\n",
        "README.md": f"# My itchy game\n\nRun `itchy run` to play. Move the player with the arrow keys and click the coin to score.\nEdit `sprite_player.py` and `sprite_coin.py` for behavior; add shared state in `vars.py` and `lists.py`.\n`game.py` discovers shared declarations automatically. Restart to see changes.\nRun `itchy build` to export `dist/game.sb3` and a browser preview.\n\n[Learn to create games in the itchy book]({BOOK}).\n",
        "assets/coin.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><circle cx="20" cy="20" r="16" fill="#fbbf24" stroke="#d97706" stroke-width="3"/></svg>\n',
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
    local_names = {path.stem for path in directory.glob('*.py')}
    previous_modules = {name: sys.modules.pop(name) for name in local_names if name in sys.modules}
    os.chdir(directory)
    sys.path.insert(0, str(directory))
    try:
        yield
    finally:
        for name in local_names:
            sys.modules.pop(name, None)
        sys.modules.update(previous_modules)
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
