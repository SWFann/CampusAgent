"""
Mock Model Server - P2 Compose Placeholder

This is a minimal HTTP server using only Python standard library.
It provides health check endpoints and a simple placeholder response.

IMPORTANT: This is NOT a real model gateway. It is a Compose placeholder
service that will be replaced or extended in P7 (Model Gateway & Edge Node).
Do not route real model requests to this service.
"""

from __future__ import annotations

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

HOST = "0.0.0.0"
PORT = 8001
SERVICE_NAME = "campus-agent-mock-model"
VERSION = "0.1.0"


class MockModelHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the mock model service."""

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health/live":
            self._send_json(200, {
                "status": "ok",
                "service": SERVICE_NAME,
            })
        elif self.path == "/health/ready":
            self._send_json(200, {
                "status": "ready",
                "service": SERVICE_NAME,
                "checks": {"model": "placeholder"},
            })
        elif self.path == "/":
            self._send_json(200, {
                "service": SERVICE_NAME,
                "version": VERSION,
                "description": "P2 Compose placeholder - not a real model gateway",
            })
        else:
            self._send_json(404, {
                "error": "not_found",
                "message": f"Path '{self.path}' is not available on mock-model",
            })

    def do_POST(self) -> None:
        """Placeholder for future model chat/completion endpoints."""
        if self.path in ("/v1/chat/completions", "/chat", "/complete"):
            self._send_json(200, {
                "id": f"mock-{int(time.time())}",
                "model": "mock-placeholder",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "[mock-model placeholder response]",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "note": "This is a P2 Compose placeholder response, not a real model output.",
            })
        else:
            self._send_json(404, {
                "error": "not_found",
                "message": f"Path '{self.path}' is not available on mock-model",
            })

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging to keep output clean."""
        pass


def main() -> None:
    server = HTTPServer((HOST, PORT), MockModelHandler)
    print(f"[{SERVICE_NAME}] Listening on {HOST}:{PORT} (P2 Compose placeholder)")
    print(f"[{SERVICE_NAME}] Health: GET /health/live, GET /health/ready")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[{SERVICE_NAME}] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
