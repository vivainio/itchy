from itchy import events, sound
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json

import pytest
from games.logic_playground import game
from itchy.build import build
from itchy.compiler import compile_game
from itchy.game import Sound


def test_png_and_wav_are_embedded_with_metadata() -> None:
    with ZipFile(BytesIO(compile_game(game))) as archive:
        project = json.loads(archive.read("project.json"))
        coin = next(target for target in project["targets"] if target["name"] == "Coin")
        image = coin["costumes"][0]
        sound = coin["sounds"][0]
        assert image["dataFormat"] == "png"
        assert archive.read(image["md5ext"]).startswith(b"\x89PNG")
        assert archive.read(sound["md5ext"]).startswith(b"RIFF")
        assert sound["rate"] == 22050
        assert sound["sampleCount"] == 4410


def test_undeclared_sound_is_rejected(tmp_path: Path) -> None:
    undeclared_sound = Sound("Missing", tmp_path / "missing.wav")
    bad = replace(game, sprites=(replace(game.sprites[0], scripts=(events.on_start(sound.play(undeclared_sound)),)),))
    with pytest.raises(ValueError, match="Undeclared sound"):
        compile_game(bad)


def test_build_contains_complete_preview_and_exports(tmp_path: Path) -> None:
    output = tmp_path / "dist"
    build(output)
    assert (output / "coin-runner.sb3").is_file()
    assert (output / "logic-playground.sb3").is_file()
    manifest = json.loads((output / "manifest.json").read_text())
    assert set(manifest["projects"]) == {"coin-runner", "logic-playground", "hide-and-seek"}
    with ZipFile(output / "itchy-preview.zip") as archive:
        for path in ("index.html", "game.sb3", "logic.sb3", "vendor/vm.js", "vendor/render.js",
                     "vendor/storage.js", "vendor/audio.js", "vendor/bitmap.js"):
            assert path in archive.namelist()
        assert any(path.startswith("chunks/") for path in archive.namelist())
