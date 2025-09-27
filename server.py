from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

from utils import (
    execute_get_request,
    render_series_html,
    render_rankings_html,
    render_teams_html,
    render_live_games_html,
    render_upcoming_games_html,
)

_HOST = "127.0.0.1"
_PORT = 8000
_UPCOMING_LIMIT = 20


class ScoreboardRequestHandler(BaseHTTPRequestHandler):
    """Basic HTTP handler serving scoreboard pages."""

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        parsed_path = urlparse(self.path)
        route = parsed_path.path

        if route in ("", "/", "/upcoming-games"):
            self._serve_upcoming_games()
        elif route == "/series":
            self._serve_series()
        elif route == "/teams":
            self._serve_teams(parse_qs(parsed_path.query))
        elif route == "/rankings":
            self._serve_rankings(parse_qs(parsed_path.query))
        elif route == "/live":
            self._serve_live()
        elif route == "/health":
            self._write_response(200, b"ok", content_type="text/plain; charset=utf-8")
        else:
            self._write_response(404, b"Not found", content_type="text/plain; charset=utf-8")

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - keeping signature
        # Reduce noise in CLI output by using default logging.
        super().log_message(format, *args)

    def _serve_upcoming_games(self) -> None:
        try:
            payload = execute_get_request()
            html = render_upcoming_games_html(payload, limit=_UPCOMING_LIMIT)
            self._write_response(200, html.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            message = f"Internal server error: {exc}".encode("utf-8")
            self._write_response(500, message, content_type="text/plain; charset=utf-8")

    def _serve_series(self) -> None:
        try:
            payload = execute_get_request()
            html = render_series_html(payload)
            self._write_response(200, html.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            message = f"Internal server error: {exc}".encode("utf-8")
            self._write_response(500, message, content_type="text/plain; charset=utf-8")

    def _serve_teams(self, query: Dict[str, List[str]]) -> None:
        try:
            selected_series = query.get("series", [None])[0]
            payload = execute_get_request()
            html = render_teams_html(payload, selected_series_uuid=selected_series)
            self._write_response(200, html.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            message = f"Internal server error: {exc}".encode("utf-8")
            self._write_response(500, message, content_type="text/plain; charset=utf-8")

    def _serve_rankings(self, query: Dict[str, List[str]]) -> None:
        try:
            selected_series = query.get("series", [None])[0]
            payload = execute_get_request()
            html = render_rankings_html(payload, selected_series_uuid=selected_series)
            self._write_response(200, html.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            message = f"Internal server error: {exc}".encode("utf-8")
            self._write_response(500, message, content_type="text/plain; charset=utf-8")

    def _serve_live(self) -> None:
        try:
            payload = execute_get_request()
            html = render_live_games_html(payload)
            self._write_response(200, html.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors
            message = f"Internal server error: {exc}".encode("utf-8")
            self._write_response(500, message, content_type="text/plain; charset=utf-8")


    def _write_response(
        self,
        status: int,
        body: bytes,
        content_type: str = "text/html; charset=utf-8",
        headers: Tuple[Tuple[str, str], ...] = (),
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for header, value in headers:
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = _HOST, port: int = _PORT) -> None:
    server_address = (host, port)
    httpd = HTTPServer(server_address, ScoreboardRequestHandler)
    print(f"Serving on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
