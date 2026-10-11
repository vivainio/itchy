from pathlib import Path
import pytest
from itchy.compiler import compile_game
from itchy.project import init_project, load_game, preview_html, project_config


def test_init_load_and_export(tmp_path: Path):
    init_project(tmp_path)
    game = load_game(tmp_path)
    assert game.name == "My first game"
    assert compile_game(game).startswith(b"PK")
    assert project_config(tmp_path) == (tmp_path / "game.py", tmp_path / "dist")
    source = (tmp_path / "game.py").read_text()
    assert "https://vivainio.github.io/itchy/" in source
    assert "https://vivainio.github.io/itchy/api/" in source
    with pytest.raises(ValueError, match="empty directory"):
        init_project(tmp_path)
    assert source == (tmp_path / "game.py").read_text()


def test_project_config_and_validation(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="itchy init"):
        load_game(tmp_path)
    (tmp_path / "itchy.toml").write_text('[project]\nentry="custom.py"\noutput="exports"\n')
    (tmp_path / "custom.py").write_text('game = "not a Game"\n')
    assert project_config(tmp_path)[1] == tmp_path / "exports"
    with pytest.raises(ValueError, match="Game named game"):
        load_game(tmp_path)
