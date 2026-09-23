"""Serve the demo pages on http://localhost:8000 (Ctrl-C to stop)."""
import http.server
import socketserver
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000
with socketserver.TCPServer(("127.0.0.1", PORT), http.server.SimpleHTTPRequestHandler) as httpd:
    print(f"Serving {os.getcwd()} on http://localhost:{PORT}")
    httpd.serve_forever()
