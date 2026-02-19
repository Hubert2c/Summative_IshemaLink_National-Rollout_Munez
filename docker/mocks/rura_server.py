"""
RURA Mock Server — simulates Rwanda Utilities Regulatory Authority license API.
All licenses starting with 'INVALID' return invalid; others return valid.
Listens on port 8002.
"""

import json, re
from http.server import BaseHTTPRequestHandler, HTTPServer


class RURAHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        match = re.match(r"/api/gov/rura/verify-license/(.+)/", self.path)
        if match:
            license_no = match.group(1)
            is_valid   = not license_no.startswith("INVALID")
            self._respond(200, {
                "license_number":   license_no,
                "valid":            is_valid,
                "insurance_active": is_valid,
                "expiry_date":      "2026-12-31" if is_valid else "2023-01-01",
                "authority":        "RURA Rwanda",
            })
        else:
            self._respond(404, {"error": "Not found"})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8002), RURAHandler)
    print("RURA Mock running on :8002")
    server.serve_forever()
