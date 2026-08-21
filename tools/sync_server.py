"""Receives a collector's harvest from the browser and writes it to disk.

The collector normally hands you a download. Chrome blocks repeated automatic
downloads from the same origin, so a second or third tournament in one sitting
silently never arrives - which looks exactly like a failed scrape. Posting to a
local server sidesteps that entirely, and http://localhost is a trustworthy
origin so an https page is allowed to reach it.

    python3 tools/sync_server.py        # listens on 8901 until Ctrl-C

Then from the page:
    fetch('http://localhost:8901', {method:'POST',
      headers:{'content-type':'application/json'},
      body: JSON.stringify({name:'rcb-<id>', text: rows.join('\\n')})})
"""
import http.server
import json
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
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        try:
            body = json.loads(self.rfile.read(n))
            name = str(body.get("name", "data")).replace("/", "_")
            text = body.get("text", "")
            OUT.mkdir(exist_ok=True)
            path = OUT / (name + ".tsv")
            path.write_text(text if text.endswith("\n") else text + "\n",
                            encoding="utf-8")
            msg = {"ok": True, "wrote": path.name, "bytes": len(text)}
            print("wrote %-26s %8d bytes" % (path.name, len(text)), flush=True)
        except Exception as e:
            msg = {"ok": False, "error": str(e)}
            print("ERROR %s" % e, flush=True)
        out = json.dumps(msg).encode()
        self.send_response(200)
        self._cors()
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass          # the prints above are the useful log


if __name__ == "__main__":
    print("listening on http://localhost:%d  ->  %s" % (PORT, OUT), flush=True)
    http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
