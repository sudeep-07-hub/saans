#!/usr/bin/env python3
"""
Saans launcher.

    python run.py            # http://127.0.0.1:8017
    python run.py --port 9000

Checks for Ollama at startup and tells you plainly whether the plans will be
written by the model or by the deterministic fallback. It does not fail if the
model is missing: the arithmetic is the product, the prose is the wrapper.
"""
from __future__ import annotations

import argparse
import socket
import sys

import uvicorn


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the Saans server")
    ap.add_argument("--port", type=int, default=8017)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()

    try:
        from saans import narrator
        ok = narrator.available()
        print(f"  model: {narrator.MODEL} -> {'ready' if ok else 'not found (deterministic plan will be used)'}")
    except Exception as exc:
        print(f"  model check failed: {exc}")

    if not port_free(args.port):
        print(f"  port {args.port} is already in use; try --port {args.port + 1}")
        return 1

    print(f"  http://{args.host}:{args.port}")
    uvicorn.run("saans.server:app", host=args.host, port=args.port,
                reload=args.reload, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
