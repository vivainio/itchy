"""Project-local runtime setup; installs Bun only when no executable is available."""
from io import BytesIO
from pathlib import Path
import platform
import shutil
import subprocess
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
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
    bun = ensure_bun()
    packages = ("scratch-vm", "scratch-render", "scratch-storage", "scratch-audio", "scratch-svg-renderer", "playwright")
    if force or not all((ROOT / "node_modules" / package).is_dir() for package in packages):
        subprocess.run([str(bun), "install", "--frozen-lockfile"], cwd=ROOT, check=True)
    return bun
