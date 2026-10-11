from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import os
import webbrowser
from pathlib import Path

from games import coin_runner, logic_playground, hide_and_seek
from itchy.compiler import compile_game
from itchy.build import build

ROOT = Path(__file__).resolve().parent.parent
VENDOR = {
    "/vendor/bitmap.js": "node_modules/scratch-svg-renderer/dist/web/scratch-svg-renderer.js",
    "/vendor/audio.js": "dist/preview/vendor/audio.js",
    "/vendor/vm.js": "node_modules/scratch-vm/dist/web/scratch-vm.js",
    "/vendor/render.js": "node_modules/scratch-render/dist/web/scratch-render.js",
    "/vendor/storage.js": "node_modules/scratch-storage/dist/web/scratch-storage.min.js",
}

for chunk in (ROOT / "node_modules/scratch-storage/dist/web/chunks").glob("*.js"):
    VENDOR[f"/chunks/{chunk.name}"] = str(chunk.relative_to(ROOT))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        content_type = "application/javascript"
        try:
            if path == "/":
                body = (ROOT / "web/index.html").read_bytes()
                content_type = "text/html; charset=utf-8"
            elif path in ("/game.sb3", "/logic.sb3", "/hide-and-seek.sb3"):
                module = {"/game.sb3": coin_runner, "/logic.sb3": logic_playground,
                          "/hide-and-seek.sb3": hide_and_seek}[path]
                body = compile_game(importlib.reload(module).game)
                content_type = "application/octet-stream"
            elif path in VENDOR:
                body = (ROOT / VENDOR[path]).read_bytes()
            else:
                self.send_error(404)
                return
        except Exception as error:
            self.send_error(500, str(error))
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if path == "/game.sb3":
            self.send_header("Content-Disposition", 'attachment; filename="coin-runner.sb3"')
        self.end_headers()
        self.wfile.write(body)


def serve(*, port: int = 4317, open_browser: bool = False) -> None:
    build()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Scratch preview: http://127.0.0.1:{port}/", flush=True)
    if open_browser:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped preview")
    finally:
        server.server_close()


def main() -> None:
    serve(port=int(os.environ.get("PORT", "4317")))


if __name__ == "__main__":
    main()
