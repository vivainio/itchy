"""Build all example projects and a self-contained local browser distribution."""
from pathlib import Path
import json
import shutil
import subprocess

from games.coin_runner import game as coin_runner
from games.hide_and_seek import game as hide_and_seek
from games.logic_playground import game as logic_playground
from itchy.compiler import compile_game
from itchy.setup import setup

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = {"coin-runner": coin_runner, "logic-playground": logic_playground, "hide-and-seek": hide_and_seek}
VENDOR = {
    "bitmap.js": "scratch-svg-renderer/dist/web/scratch-svg-renderer.js",
    "vm.js": "scratch-vm/dist/web/scratch-vm.js",
    "render.js": "scratch-render/dist/web/scratch-render.js",
    "storage.js": "scratch-storage/dist/web/scratch-storage.min.js",
}


def build(output: Path = ROOT / "dist") -> None:
    bun = setup()
    preview = output / "preview"
    vendor = preview / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"projects": {}, "preview": "preview/index.html"}
    projects: dict[str, str] = {}
    for name, game in EXAMPLES.items():
        exported = compile_game(game)
        (output / f"{name}.sb3").write_bytes(exported)
        (preview / f"{name}.sb3").write_bytes(exported)
        projects[name] = f"{name}.sb3"
    manifest["projects"] = projects
    shutil.copyfile(preview / "coin-runner.sb3", preview / "game.sb3")
    shutil.copyfile(preview / "logic-playground.sb3", preview / "logic.sb3")
    shutil.copyfile(ROOT / "web/index.html", preview / "index.html")
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
    print(f"Built {len(EXAMPLES)} Scratch projects and {output / 'itchy-preview.zip'}")


def main() -> None:
    build()
    subprocess.run([str(ROOT / ".venv/bin/zensical"), "build", "--clean", "--strict"], cwd=ROOT, check=True)
    subprocess.run(["uv", "build", "--out-dir", str(ROOT / "dist/packages")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
