#!/usr/bin/env python3
"""Local DST live-data simulator for the offline PTA browser app.

Run:
  python3 dst-live-data-simulator.py

Then open:
  http://127.0.0.1:4180/dst-pressure-transient-analysis.html

Live JSON endpoint:
  http://127.0.0.1:4180/dst/live?batch=8
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
START_TIME = datetime(2026, 6, 21, 8, 0, tzinfo=timezone.utc)


class SimulatorState:
    def __init__(self) -> None:
        self.rows = build_dst_rows()
        self.cursor = 0

    def reset(self) -> None:
        self.cursor = 0

    def next_rows(self, batch: int) -> list[dict[str, float | str]]:
        batch = max(1, min(batch, 200))
        if self.cursor >= len(self.rows):
          return [self.rows[-1]]
        rows = self.rows[self.cursor : self.cursor + batch]
        self.cursor = min(len(self.rows), self.cursor + batch)
        return rows


STATE = SimulatorState()


def build_dst_rows() -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []

    def add(minutes: float, bhp: float, oil: float, water: float, gas: float, whp: float, temp: float) -> None:
        timestamp = START_TIME + timedelta(minutes=minutes)
        rows.append(
            {
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "bhp_psi": round(bhp, 2),
                "oil_bpd": round(oil, 2),
                "water_bpd": round(water, 2),
                "gas_mscfd": round(gas, 2),
                "rate_bpd": round(oil + water, 2),
                "whp_psi": round(whp, 2),
                "temp_f": round(temp, 2),
            }
        )

    for i in range(11):
        add(i * 8, 8420 - 88 * math.log10(i + 1), 0, 0, 0, 430 + i * 1.5, 184 + i * 0.08)

    for i in range(1, 17):
        rate = 260 + i * 18 + math.sin(i / 2) * 28
        add(80 + i * 10, 8320 - 95 * math.log10(i + 1) - i * 6, rate, 35 if i < 6 else 10, 0, 570 + i * 2.1, 185 + i * 0.14)

    for i in range(1, 10):
        add(250 + i * 7, 7700 + i * 22, 0, 0, 0, 510 - i * 1.4, 188 - i * 0.04)

    for i in range(1, 11):
        rate = 560 + math.sin(i) * 35
        add(330 + i * 8, 7830 - 50 * math.log10(i + 1), rate, 6, 0, 610 + i * 1.8, 187 + i * 0.04)

    shut_start = 420
    for i in range(45):
        minutes = shut_start + i * (5 if i < 10 else 10)
        dt_hr = max(0.02, (minutes - shut_start) / 60)
        buildup = 520 * (1 - math.exp(-dt_hr / 1.55)) + 72 * math.log10(dt_hr + 1)
        storage = -35 + i * 8 if i < 5 else 0
        noise = math.sin(i * 1.33) * 2.2
        add(minutes, 7745 + buildup + storage + noise, 0, 0, 0, 500 - i * 0.8, 189 - i * 0.025)

    return rows


class Handler(BaseHTTPRequestHandler):
    server_version = "DSTLiveSimulator/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/dst/live":
            self._serve_live(parsed.query)
            return
        if parsed.path == "/dst/reset":
            STATE.reset()
            self._json({"ok": True, "message": "simulator reset", "rows": len(STATE.rows)})
            return
        if parsed.path == "/dst/status":
            self._json({"rows": len(STATE.rows), "cursor": STATE.cursor, "remaining": max(0, len(STATE.rows) - STATE.cursor)})
            return
        self._serve_static(parsed.path)

    def _serve_live(self, query: str) -> None:
        params = parse_qs(query)
        batch = int(params.get("batch", ["1"])[0] or 1)
        rows = STATE.next_rows(batch)
        self._json({"rows": rows, "cursor": STATE.cursor, "remaining": max(0, len(STATE.rows) - STATE.cursor)})

    def _serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/dst-pressure-transient-analysis.html"
        target = (ROOT / path.lstrip("/")).resolve()
        if not str(target).startswith(str(ROOT)) or not target.is_file():
            self.send_error(404, "File not found")
            return
        data = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, payload: dict) -> None:
        data = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve simulated real-time DST data for the PTA app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4180)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"DST live simulator running at http://{args.host}:{args.port}/")
    print(f"Endpoint: http://{args.host}:{args.port}/dst/live?batch=8")
    server.serve_forever()


if __name__ == "__main__":
    main()
