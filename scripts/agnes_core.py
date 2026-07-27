#!/usr/bin/env python3
"""Shared curl transport and file helpers for Agnes media generation."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import getproxies

API_ROOT = "https://apihub.agnes-ai.com"
IMAGE_MODEL = "agnes-image-2.0-flash"
VIDEO_MODEL = "agnes-video-v2.0"
RETRYABLE_STATUS = {429, 500, 502, 503, 520}
TRANSPORT = 'curl auto routing (HTTP/1.1; no forced proxy or bypass)'


class AgnesError(RuntimeError):
    pass


def api_key() -> str:
    value = os.environ.get("AGNES_API_KEY", "").strip()
    if not value:
        raise AgnesError("AGNES_API_KEY is not set.")
    return value


def curl_executable() -> str:
    value = shutil.which("curl.exe") or shutil.which("curl")
    if not value:
        raise AgnesError("curl/curl.exe was not found in PATH.")
    return value


def _parse_curl_response(stdout: str) -> tuple[str, int]:
    marker = "\n__AGNES_HTTP_STATUS__:"
    if marker not in stdout:
        return stdout, 0
    body, tail = stdout.rsplit(marker, 1)
    try:
        status = int(tail.strip().splitlines()[0])
    except (ValueError, IndexError):
        status = 0
    return body, status


def _run_curl_with_heartbeat(
    args: list[str],
    *,
    input_text: str | None,
    operation: str,
    heartbeat_seconds: float = 15,
) -> tuple[int, str, str]:
    """Run curl while emitting periodic progress so agent hosts do not treat it as silent."""
    print(f"agnes: starting {operation}", file=sys.stderr, flush=True)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
        )
        if input_text is not None and process.stdin is not None:
            process.stdin.write(input_text.encode("utf-8"))
            process.stdin.close()

        started = time.monotonic()
        next_heartbeat = started + heartbeat_seconds
        try:
            while process.poll() is None:
                now = time.monotonic()
                if now >= next_heartbeat:
                    elapsed = int(now - started)
                    print(f"agnes: {operation} still running ({elapsed}s)", file=sys.stderr, flush=True)
                    next_heartbeat = now + heartbeat_seconds
                time.sleep(0.25)
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            raise

        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode("utf-8", errors="replace")
        stderr = stderr_file.read().decode("utf-8", errors="replace")
        return process.returncode or 0, stdout, stderr.strip()


def _curl_json_once(
    method: str,
    url: str,
    payload_path: Path | None,
    timeout: float,
    operation: str,
) -> tuple[int, str, str, int]:
    args = [
        curl_executable(),
        "--silent",
        "--show-error",
        "--http1.1",
        "--connect-timeout",
        "30",
        "--max-time",
        str(timeout),
        "--request",
        method,
        "--url",
        url,
        "--header",
        "Accept: application/json",
        "--write-out",
        "\n__AGNES_HTTP_STATUS__:%{http_code}\n",
        "--config",
        "-",
    ]
    if payload_path is not None:
        args.extend([
            "--header",
            "Content-Type: application/json",
            "--data-binary",
            f"@{payload_path}",
        ])

    # Keep the API key out of the process command line and terminal output.
    config_stdin = f'header = "Authorization: Bearer {api_key()}"\n'
    returncode, stdout, stderr = _run_curl_with_heartbeat(
        args, input_text=config_stdin, operation=operation
    )
    body, status = _parse_curl_response(stdout)
    return returncode, body, stderr, status


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: float = 180,
    retries: int = 2,
    operation: str = "API request",
) -> dict[str, Any]:
    payload_path: Path | None = None
    try:
        if body is not None:
            fd, name = tempfile.mkstemp(prefix="agnes-request-", suffix=".json")
            os.close(fd)
            payload_path = Path(name)
            payload_path.write_text(
                json.dumps(body, ensure_ascii=False),
                encoding="utf-8",
            )

        for attempt in range(retries + 1):
            if attempt > 0:
                print(
                    f"agnes: retrying {operation} (attempt {attempt + 1}/{retries + 1})",
                    file=sys.stderr,
                    flush=True,
                )
            returncode, raw, stderr, status = _curl_json_once(
                method, url, payload_path, timeout, operation
            )

            retryable = returncode != 0 or status in RETRYABLE_STATUS
            if retryable and attempt < retries:
                time.sleep(min(2**attempt, 8))
                continue

            if returncode != 0:
                detail = stderr or raw.strip() or f"curl exit code {returncode}"
                raise AgnesError(f"curl network error: {detail}")
            if status >= 400:
                raise AgnesError(f"HTTP {status}: {raw.strip()}")
            if status == 0:
                raise AgnesError(
                    "curl returned no HTTP status. "
                    f"stderr={stderr or '<empty>'}; body={raw[:500]!r}"
                )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AgnesError(
                    f"API returned invalid JSON (HTTP {status}): {exc}; "
                    f"body={raw[:1000]!r}"
                ) from None
            if not isinstance(parsed, dict):
                raise AgnesError("API returned a non-object JSON response.")
            return parsed
    finally:
        if payload_path is not None:
            try:
                payload_path.unlink(missing_ok=True)
            except OSError:
                pass

    raise AgnesError("Request failed after retries.")


def image_value(value: str) -> str:
    if value.startswith(("https://", "http://", "data:")):
        return value
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise AgnesError(f"Image input does not exist: {path}")
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def download(url: str, destination: str, timeout: float, retries: int = 2) -> Path:
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".part")

    for attempt in range(retries + 1):
        partial.unlink(missing_ok=True)
        args = [
            curl_executable(),
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--http1.1",
            "--connect-timeout",
            "30",
            "--max-time",
            str(timeout),
            "--output",
            str(partial),
            url,
        ]
        if attempt > 0:
            print(
                f"agnes: retrying output download (attempt {attempt + 1}/{retries + 1})",
                file=sys.stderr,
                flush=True,
            )
        returncode, _stdout, stderr = _run_curl_with_heartbeat(
            args, input_text=None, operation="output download"
        )
        if returncode == 0 and partial.is_file() and partial.stat().st_size > 0:
            os.replace(partial, output)
            return output
        if attempt < retries:
            time.sleep(min(2**attempt, 8))
            continue
        partial.unlink(missing_ok=True)
        detail = stderr or f"curl exit code {returncode}"
        raise AgnesError(f"Could not download result by curl: {detail}")

    raise AgnesError("Could not download result after retries.")


def write_base64(data: str, destination: str) -> Path:
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.write_bytes(base64.b64decode(data, validate=True))
    except ValueError as exc:
        raise AgnesError(f"Invalid Base64 image response: {exc}") from None
    return output


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), flush=True)
