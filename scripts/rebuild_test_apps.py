"""Re-import, type-check, and build local test-apps/*.sb3 projects."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    apps = root / "test-apps"
    apps.mkdir(exist_ok=True)
    sources = sorted(apps.glob("*.sb3"))
    if not sources:
        print(f"No .sb3 files found in {apps}")
        return
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(root), environment.get("PYTHONPATH")))
    )
    for source in sources:
        destination = apps / f"{source.stem}-python"
        print(f"Rebuilding {source.name} → {destination.name}", flush=True)
        if destination.is_symlink():
            destination.unlink()
        elif destination.exists():
            shutil.rmtree(destination)
        subprocess.run(
            [sys.executable, "-m", "itchy.cli", "import", str(source), str(destination)],
            cwd=root, env=environment, check=True,
        )
        subprocess.run(
            [str(Path(sys.executable).parent / "ty"), "check", "--project", str(root),
             "--extra-search-path", str(destination), "--output-format", "concise", str(destination)],
            cwd=root, env=environment, check=True,
        )
        subprocess.run(
            [sys.executable, "-m", "itchy.cli", "build"],
            cwd=destination, env=environment, check=True,
        )


if __name__ == "__main__":
    main()
