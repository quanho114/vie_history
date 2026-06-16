#!/usr/bin/env python3
"""Simple proxy server that serves static files and proxies API requests."""

import http.server
import socketserver
import urllib.request
import urllib.parse
import os
import re
import mimetypes

PORT = 12702
API_TARGET = "http://localhost:12701"
DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

# Try to set custom directory for serving
class SPAProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)
    
    def do_GET(self):
        """Handle GET requests - serve static files or index.html for SPA."""
        # Proxy API requests
        if self.path.startswith("/api/"):
            self.proxy_request()
            return
        
        # Check if it's a static file
        path = self.path.split('?')[0]  # Remove query string
        static_file = os.path.join(DIST_DIR, path.lstrip('/'))
        
        if os.path.isfile(static_file):
            # Serve static file directly
            super().do_GET()
        elif os.path.isfile(os.path.join(DIST_DIR, path.lstrip('/'), "index.html")):
            # Serve index.html for directory
            self.path = os.path.join(path, "index.html")
            super().do_GET()
        else:
            # Serve index.html for SPA routing (React Router)
            self.path = "/index.html"
            super().do_GET()
    
    def do_POST(self):
        # Proxy POST requests to API
        if self.path.startswith("/api/"):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def do_PUT(self):
        if self.path.startswith("/api/"):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self.proxy_request()
        else:
            self.send_error(404)
    
    def proxy_request(self):
        """Forward request to API backend."""
        target = API_TARGET + self.path
        print(f"Proxy: {self.path} -> {target}")
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Prepare headers
            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in ('host', 'connection'):
                    headers[key] = value
            
            # Make request
            req = urllib.request.Request(
                target,
                data=body,
                headers=headers,
                method=self.command
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                self.send_response(response.status)
                
                # Forward response headers
                for key, value in response.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(key, value)
                self.end_headers()
                
                # Forward response body
                self.wfile.write(response.read())
                
        except Exception as e:
            print(f"Proxy error: {e}")
            self.send_error(502, str(e))

if __name__ == "__main__":
    print(f"Starting proxy server on port {PORT}")
    print(f"Serving static files from: {DIST_DIR}")
    print(f"Proxying API to: {API_TARGET}")
    print(f"")
    print(f"Access: http://localhost:{PORT}")
    
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), SPAProxyHandler) as httpd:
        httpd.serve_forever()
