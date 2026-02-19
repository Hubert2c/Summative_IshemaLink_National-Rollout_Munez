"""
EBM Mock Server — simulates Rwanda Revenue Authority EBM API.
Run: python ebm_server.py
Listens on port 8001.
"""

import hashlib, json, uuid
from http.server import BaseHTTPRequestHandler, HTTPServer


class EBMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/ebm/sign/":
            length = int(self.headers.get("Content-Length", 0))
            body   = json.loads(self.rfile.read(length))

            receipt_num = f"EBM-RW-{uuid.uuid4().hex[:8].upper()}"
            signature   = hashlib.sha256(
                f"{body['transaction_id']}{body['amount']}{receipt_num}".encode()
            ).hexdigest()

            self._respond(200, {
                "receipt_number": receipt_num,
                "signature":      signature,
                "timestamp":      body.get("timestamp", ""),
                "authority":      "Rwanda Revenue Authority",
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
    server = HTTPServer(("0.0.0.0", 8001), EBMHandler)
    print("EBM Mock running on :8001")
    server.serve_forever()
