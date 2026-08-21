"""Receives harvested league data from the browser and writes it to disk.

CricHeroes sits behind Cloudflare and renders its detail client-side, so the
data can only be read from inside a real browser session. The browser cannot
write files, so the collector posts what it harvested here and this writes it
out. http://localhost is a trustworthy origin in Chrome, so an https page is
allowed to post to it.

    python3 tools/sync_server.py          # listens on 8901 until Ctrl-C
"""
import http.server, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "league-raw"
PORT = 8901


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(n))
            name = str(body.get("name", "data")).replace("/", "_")
            OUT.mkdir(exist_ok=True)
            path = OUT / (name + ".tsv")
            path.write_text(body.get("text", ""), encoding="utf-8")
            msg = {"ok": True, "wrote": path.name, "bytes": len(body.get("text", ""))}
            print("wrote %-18s %7d bytes" % (path.name, msg["bytes"]), flush=True)
        except Exception as e:
            msg = {"ok": False, "error": str(e)}
            print("ERROR", e, flush=True)
        out = json.dumps(msg).encode()
        self.send_response(200); self._cors()
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("listening on http://localhost:%d  ->  %s" % (PORT, OUT), flush=True)
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
