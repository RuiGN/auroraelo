#!/usr/bin/env python3
"""Servidor estático local com fallback para index.html (SPA), só para conferir exports web.
Uso: python3 scripts/serve-spa.py [pasta] [porta]"""
import http.server
import os
import sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "dist-preview")
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8790


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=root, **kwargs)

    def send_head(self):
        path = self.translate_path(self.path)
        if not os.path.exists(path) and "." not in os.path.basename(self.path):
            self.path = "/index.html"
        return super().send_head()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
