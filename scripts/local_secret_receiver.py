"""One-session localhost form for copying browser-created service keys into .env.

Run only during setup, then stop the process. Values never appear in logs.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs
import os
import secrets


ROOT = Path(__file__).resolve().parents[1]
ROUTE = "/" + secrets.token_urlsafe(18)
ALLOWED = {
    "HF_API_TOKEN",
    "IRIS_AGENT_MEMORY_API_KEY",
    "IRIS_LANGCACHE_API_KEY",
    "IRIS_CONTEXT_AGENT_KEY",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != ROUTE:
            self.send_error(404)
            return
        body = b'''<!doctype html><title>Reachy local secret import</title>
<h1>Reachy local secret import</h1>
<label>Variable <select id="name"><option>HF_API_TOKEN</option><option>IRIS_AGENT_MEMORY_API_KEY</option><option>IRIS_LANGCACHE_API_KEY</option><option>IRIS_CONTEXT_AGENT_KEY</option></select></label>
<label>Value <input id="value" type="password" autocomplete="off"></label>
<button id="save">Save locally</button><p id="status"></p>
<script>document.getElementById("save").onclick=async()=>{let n=document.getElementById("name").value,v=document.getElementById("value").value;let r=await fetch(location.pathname,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams({name:n,value:v})});document.getElementById("status").textContent=await r.text();document.getElementById("value").value=""}</script>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != ROUTE:
            self.send_error(404)
            return
        size = min(int(self.headers.get("Content-Length", "0")), 8192)
        data = parse_qs(self.rfile.read(size).decode())
        name = data.get("name", [""])[0]
        value = data.get("value", [""])[0]
        if name not in ALLOWED or not value or "\n" in value or "\r" in value:
            self.send_error(400)
            return
        path = ROOT / ".env"
        lines = path.read_text().splitlines()
        lines = [f"{name}={value}" if line.startswith(name + "=") else line for line in lines]
        path.write_text("\n".join(lines) + "\n")
        os.chmod(path, 0o600)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write((name + " saved locally").encode())


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 0), Handler)
    print(f"http://127.0.0.1:{server.server_port}{ROUTE}", flush=True)
    server.serve_forever()
