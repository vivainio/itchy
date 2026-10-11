import argparse
import subprocess
import sys

from itchy import build, server
from itchy.setup import ROOT, setup


def main() -> None:
    parser = argparse.ArgumentParser(prog="itchy", description="Typed Python games → Scratch blocks and .sb3 projects")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Set up, build, serve, and open the local Scratch player")
    run.add_argument("--port", type=int, default=4317)
    run.add_argument("--no-open", action="store_true", help="Start the server without opening a browser")
    commands.add_parser("build", help="Build Scratch exports, offline preview ZIP, wheel, and source package")
    commands.add_parser("setup", help="Install project-local Bun and Scratch runtime dependencies")
    commands.add_parser("check", help="Check all Python source with ty")
    tests = commands.add_parser("test", help="Run Python/VM tests")
    tests.add_argument("--browser", action="store_true", help="Also install Chromium and verify the browser preview")
    tests.add_argument("--preview", action="store_true", help="Also verify the built static preview")
    args = parser.parse_args()
    match args.command:
        case "run": server.serve(port=args.port, open_browser=not args.no_open)
        case "build": build.main()
        case "setup": setup(force=True)
        case "check": subprocess.run([str(ROOT / ".venv/bin/ty"), "check"], cwd=ROOT, check=True)
        case "test":
            bun = setup()
            subprocess.run([sys.executable, "-m", "pytest"], cwd=ROOT, check=True)
            if args.browser or args.preview:
                subprocess.run([str(bun), "x", "playwright", "install", "chromium"], cwd=ROOT, check=True)
                if args.preview:
                    build.build()
                command = [str(bun), "runner/browser-test.js"]
                if args.preview:
                    command.append("--static")
                subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
