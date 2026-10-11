from pathlib import Path
import pytest
from itchy.compiler import compile_game
from itchy.project import init_project, load_game, preview_html, project_config


def test_init_load_and_export(tmp_path: Path):
    init_project(tmp_path)
    game = load_game(tmp_path)
    assert game.name == "My first game"
    assert [sprite.name for sprite in game.sprites] == ["Player", "Coin"]
    assert [variable.name for variable in game.variables] == ["score", "status"]
    assert [item.name for item in game.lists] == ["collected"]
    assert game.stage is not None
    assert compile_game(game).startswith(b"PK")
    assert project_config(tmp_path) == (tmp_path / "game.py", tmp_path / "dist")
    source = (tmp_path / "game.py").read_text()
    assert "https://vivainio.github.io/itchy/" in source
    assert "https://vivainio.github.io/itchy/api/" in source
    with pytest.raises(ValueError, match="empty directory"):
        init_project(tmp_path)
    assert source == (tmp_path / "game.py").read_text()


def test_starter_discovers_shared_declarations_and_reloads(tmp_path: Path):
    init_project(tmp_path)
    with (tmp_path / "vars.py").open("a") as source:
        source.write('\nhealth = Num("health", 3)\nlabel = String("label", "ready")\nhelper = 42\n')
    with (tmp_path / "lists.py").open("a") as source:
        source.write('\ninventory = ScratchList("inventory", ("key",))\n')
    game = load_game(tmp_path)
    assert [value.name for value in game.variables] == ["score", "status", "health", "label"]
    assert [value.name for value in game.lists] == ["collected", "inventory"]
    assert compile_game(game).startswith(b"PK")
    other = tmp_path / "another"
    init_project(other)
    assert [value.name for value in load_game(other).variables] == ["score", "status"]


def test_project_config_and_validation(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="itchy init"):
        load_game(tmp_path)
    (tmp_path / "itchy.toml").write_text('[project]\nentry="custom.py"\noutput="exports"\n')
    (tmp_path / "custom.py").write_text('game = "not a Game"\n')
    assert project_config(tmp_path)[1] == tmp_path / "exports"
    with pytest.raises(ValueError, match="Game named game"):
        load_game(tmp_path)
