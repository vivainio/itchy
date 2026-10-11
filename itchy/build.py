"""Build all example projects and a self-contained local browser distribution."""
from pathlib import Path
import json
import shutil
import subprocess

from itchy.compiler import compile_game
from itchy.game import Game
from itchy.project import load_game, preview_html, project_config, project_context
from itchy.setup import ROOT, SOURCE_CHECKOUT, setup


def example_games() -> dict[str, Game]:
    from games.coin_runner import game as coin_runner
    from games.hide_and_seek import game as hide_and_seek
    from games.logic_playground import game as logic_playground
    return {"coin-runner": coin_runner, "logic-playground": logic_playground, "hide-and-seek": hide_and_seek}
VENDOR = {
    "bitmap.js": "scratch-svg-renderer/dist/web/scratch-svg-renderer.js",
    "vm.js": "scratch-vm/dist/web/scratch-vm.js",
    "render.js": "scratch-render/dist/web/scratch-render.js",
    "storage.js": "scratch-storage/dist/web/scratch-storage.min.js",
}


def build(output: Path | None = None, *, project: Path | None = None) -> None:
    if project is None and ((Path.cwd() / "itchy.toml").is_file() or not SOURCE_CHECKOUT):
        project = Path.cwd()
    if project is not None:
        project = project.resolve()
        _, configured_output = project_config(project)
        games = {"game": load_game(project)}
        output = output or configured_output
    else:
        games = example_games()
        output = output or ROOT / "dist"
    output = output.resolve()
    bun = setup()
    preview = output / "preview"
    vendor = preview / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"projects": {}, "preview": "preview/index.html"}
    projects: dict[str, str] = {}
    for name, game in games.items():
        if project is not None:
            with project_context(project):
                exported = compile_game(game)
        else:
            exported = compile_game(game)
        (output / f"{name}.sb3").write_bytes(exported)
        (preview / f"{name}.sb3").write_bytes(exported)
        projects[name] = f"{name}.sb3"
    manifest["projects"] = projects
    template = (ROOT / "web/index.html").read_text()
    if project is None:
        shutil.copyfile(preview / "coin-runner.sb3", preview / "game.sb3")
        shutil.copyfile(preview / "logic-playground.sb3", preview / "logic.sb3")
    else:
        template = preview_html(template, games["game"])
    (preview / "index.html").write_text(template)
    for name, path in VENDOR.items():
        source = ROOT / "node_modules" / path
        shutil.copyfile(source, vendor / name)
        for suffix in (".map", ".LICENSE.txt"):
            if Path(f"{source}{suffix}").is_file():
                shutil.copyfile(f"{source}{suffix}", vendor / f"{source.name}{suffix}")
    shutil.copytree(ROOT / "node_modules/scratch-storage/dist/web/chunks", preview / "chunks", dirs_exist_ok=True)
    subprocess.run([
        str(bun), "build", "runner/audio.js", "--target", "browser",
        "--outdir", str(vendor), "--sourcemap=external",
    ], cwd=ROOT, check=True)
    for package in ("scratch-vm", "scratch-render", "scratch-storage", "scratch-audio", "scratch-svg-renderer"):
        source = ROOT / "node_modules" / package
        destination = preview / "third-party" / package
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("LICENSE", "LICENSE.txt", "README.md", "package.json"):
            if (source / name).is_file():
                shutil.copyfile(source / name, destination / name)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.make_archive(str(output / "itchy-preview"), "zip", preview)
    print(f"Built {len(games)} Scratch projects and {output / 'itchy-preview.zip'}")


def main() -> None:
    build()
    if not SOURCE_CHECKOUT or (Path.cwd() / "itchy.toml").is_file():
        return
    subprocess.run([str(ROOT / ".venv/bin/zensical"), "build", "--clean", "--strict"], cwd=ROOT, check=True)
    subprocess.run(["uv", "build", "--out-dir", str(ROOT / "dist/packages")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
