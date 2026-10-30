from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"


class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        request_path = path.split("?", 1)[0]
        if request_path in {"/", "/login", "/register"}:
            request_path = "/index.html"
        elif request_path == "/assets/app.js":
            request_path = "/app.js"
        elif request_path == "/assets/styles.css":
            request_path = "/styles.css"
        return super().translate_path(request_path)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), FrontendHandler)
    print("SkillMatch frontend running at http://127.0.0.1:5500")
    server.serve_forever()
