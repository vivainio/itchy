"""Project-local runtime setup; installs Bun only when no executable is available."""
from io import BytesIO
from pathlib import Path
import os
import platform
from importlib.metadata import version
import shutil
import subprocess
from urllib.request import urlopen
from zipfile import ZipFile

SOURCE_ROOT = Path(__file__).resolve().parent.parent
SOURCE_CHECKOUT = (SOURCE_ROOT / "pyproject.toml").is_file() and (SOURCE_ROOT / "runner").is_dir()


def runtime_root() -> Path:
    if SOURCE_CHECKOUT:
        return SOURCE_ROOT
    if cache_override := os.environ.get("ITCHY_CACHE_DIR"):
        cache = Path(cache_override).expanduser()
    elif platform.system() == "Darwin":
        cache = Path.home() / "Library/Caches/itchy"
    elif platform.system() == "Windows":
        cache = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "itchy"
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "itchy"
    return cache / version("itchy")


ROOT = runtime_root()


def prepare_runtime() -> None:
    if not SOURCE_CHECKOUT:
        payload = Path(__file__).resolve().parent / "_runtime"
        shutil.copytree(payload, ROOT, dirs_exist_ok=True)

BUN_VERSION = "1.4.3"


def ensure_bun() -> Path:
    installed = shutil.which("bun")
    if installed:
        return Path(installed)
    for path in (ROOT / ".tools/bun-local/bun", ROOT / ".tools/bun-darwin-aarch64/bun"):
        if path.is_file():
            return path
    system = {"Darwin": "darwin", "Linux": "linux"}.get(platform.system())
    arch = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x64", "AMD64": "x64"}.get(platform.machine())
    if system is None or arch is None:
        raise RuntimeError("Install Bun manually on this platform before using itchy run")
    artifact = f"bun-{system}-{arch}"
    url = f"https://github.com/oven-sh/bun/releases/download/bun-v{BUN_VERSION}/{artifact}.zip"
    print(f"Downloading Bun {BUN_VERSION} into .tools/", flush=True)
    with urlopen(url, timeout=60) as response:
        data = response.read()
    with ZipFile(BytesIO(data)) as archive:
        binary = archive.read(f"{artifact}/bun")
    destination = ROOT / ".tools/bun-local/bun"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(binary)
    destination.chmod(0o755)
    return destination


def setup(*, force: bool = False) -> Path:
    prepare_runtime()
    bun = ensure_bun()
    packages = ("scratch-vm", "scratch-render", "scratch-storage", "scratch-audio", "scratch-svg-renderer", "playwright")
    if force or not all((ROOT / "node_modules" / package).is_dir() for package in packages):
        subprocess.run([str(bun), "install", "--frozen-lockfile"], cwd=ROOT, check=True)
    return bun
