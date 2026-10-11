import argparse
import subprocess
import sys
from pathlib import Path
from itchy.project import init_project

from itchy import build, server
from itchy.setup import ROOT, SOURCE_CHECKOUT, setup


def main() -> None:
    parser = argparse.ArgumentParser(prog="itchy", description="Typed Python games → Scratch blocks and .sb3 projects")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create a starter game in an empty directory")
    init.add_argument("directory", nargs="?", default=".")
    run = commands.add_parser("run", help="Set up, build, serve, and open the local Scratch player")
    run.add_argument("--port", type=int, default=4317)
    run.add_argument("--no-open", action="store_true", help="Start the server without opening a browser")
    commands.add_parser("build", help="Build Scratch exports and offline preview (plus docs/packages in a checkout)")
    commands.add_parser("setup", help="Install project-local Bun and Scratch runtime dependencies")
    commands.add_parser("check", help="Check all Python source with ty")
    tests = commands.add_parser("test", help="Run Python/VM tests")
    tests.add_argument("--browser", action="store_true", help="Also install Chromium and verify the browser preview")
    tests.add_argument("--preview", action="store_true", help="Also verify the built static preview")
    args = parser.parse_args()
    if args.command in ("check", "test") and not SOURCE_CHECKOUT:
        parser.error(f"itchy {args.command} requires a source checkout with development dependencies")
    match args.command:
        case "init":
            try:
                init_project(Path(args.directory))
            except ValueError as error:
                parser.error(str(error))
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
