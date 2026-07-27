#!/usr/bin/env python3
"""Video generation, polling, downloading, and diagnostics."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import getproxies

from agnes_core import (
    API_ROOT, VIDEO_MODEL, TRANSPORT, AgnesError, curl_executable,
    download, print_json, request_json,
)

def validate_video_args(args: argparse.Namespace) -> None:
    if args.num_frames > 441 or args.num_frames < 1 or (args.num_frames - 1) % 8 != 0:
        raise AgnesError("--num-frames must be <= 441 and follow the 8n + 1 rule.")
    if not 1 <= args.frame_rate <= 60:
        raise AgnesError("--frame-rate must be between 1 and 60.")
    if args.image and args.keyframe:
        raise AgnesError("Use either --image or --keyframe, not both.")
    if args.keyframe and len(args.keyframe) < 2:
        raise AgnesError("Keyframe animation requires at least two --keyframe URLs.")
    for value in ([args.image] if args.image else []) + (args.keyframe or []):
        if not value.startswith("https://"):
            raise AgnesError("Video image inputs must be publicly accessible HTTPS URLs.")


def poll_video(
    video_id: str,
    *,
    interval: float,
    timeout: float,
    request_timeout: float,
    retries: int,
    model_name: str | None,
) -> dict[str, Any]:
    started = time.monotonic()
    params = {"video_id": video_id}
    if model_name:
        params["model_name"] = model_name
    url = f"{API_ROOT}/agnesapi?{urlencode(params)}"

    while True:
        result = request_json(
            "GET", url, timeout=request_timeout, retries=retries, operation="video status request"
        )
        status = str(result.get("status", "")).lower()
        print(
            f"status={status or 'unknown'} progress={result.get('progress', 'unknown')}%",
            file=sys.stderr,
            flush=True,
        )
        if status == "completed":
            return result
        if status == "failed":
            raise AgnesError(
                f"Video task failed: {json.dumps(result.get('error'), ensure_ascii=False)}"
            )
        if time.monotonic() - started >= timeout:
            raise AgnesError(f"Polling timed out after {timeout:g} seconds; video_id={video_id}")
        time.sleep(interval)


def finish_video(result: dict[str, Any], output: str | None, request_timeout: float) -> None:
    metadata = result.get("metadata")
    url = metadata.get("url") if isinstance(metadata, dict) else None
    saved = download(str(url), output, request_timeout) if output and url else None
    summary = {
        "model": result.get("model", VIDEO_MODEL),
        "video_id": result.get("video_id"),
        "task_id": result.get("task_id") or result.get("id"),
        "status": result.get("status"),
        "progress": result.get("progress"),
        "seconds": result.get("seconds"),
        "size": result.get("size"),
        "url": url,
        "output": str(saved) if saved else None,
        "size_mapping": metadata.get("size_mapping") if isinstance(metadata, dict) else None,
        "transport": TRANSPORT,
    }
    print_json(summary)


def run_video(args: argparse.Namespace) -> None:
    validate_video_args(args)
    body: dict[str, Any] = {
        "model": VIDEO_MODEL,
        "prompt": args.prompt,
        "height": args.height,
        "width": args.width,
        "num_frames": args.num_frames,
        "frame_rate": args.frame_rate,
    }
    if args.image:
        body["image"] = args.image
    if args.keyframe:
        body["extra_body"] = {"image": args.keyframe, "mode": "keyframes"}
    if args.num_inference_steps is not None:
        body["num_inference_steps"] = args.num_inference_steps
    if args.seed is not None:
        body["seed"] = args.seed
    if args.negative_prompt:
        body["negative_prompt"] = args.negative_prompt

    created = request_json(
        "POST", f"{API_ROOT}/v1/videos", body,
        timeout=args.request_timeout, retries=args.retries, operation="video task creation"
    )
    video_id = created.get("video_id")
    if not video_id:
        raise AgnesError(
            f"Create response has no video_id: {json.dumps(created, ensure_ascii=False)}"
        )
    if not args.poll:
        print_json(created)
        return
    result = poll_video(
        str(video_id),
        interval=args.interval,
        timeout=args.poll_timeout,
        request_timeout=args.request_timeout,
        retries=args.retries,
        model_name=VIDEO_MODEL,
    )
    finish_video(result, args.output, args.request_timeout)


def run_video_status(args: argparse.Namespace) -> None:
    if args.poll:
        result = poll_video(
            args.video_id,
            interval=args.interval,
            timeout=args.poll_timeout,
            request_timeout=args.request_timeout,
            retries=args.retries,
            model_name=args.model_name,
        )
    else:
        params = {"video_id": args.video_id}
        if args.model_name:
            params["model_name"] = args.model_name
        result = request_json(
            "GET",
            f"{API_ROOT}/agnesapi?{urlencode(params)}",
            timeout=args.request_timeout,
            retries=args.retries,
            operation="video status request",
        )
    finish_video(result, args.output, args.request_timeout)


def run_diagnose(args: argparse.Namespace) -> None:
    host = "apihub.agnes-ai.com"
    addresses = sorted(
        {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    )
    curl = curl_executable()
    probe_args = [
        curl,
        "--silent",
        "--show-error",
        "--head",
        "--http1.1",
        "--connect-timeout",
        "15",
        "--max-time",
        str(args.timeout),
        "--output",
        os.devnull,
        "--write-out",
        "%{http_code}",
        API_ROOT + "/",
    ]
    completed = subprocess.run(
        probe_args,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise AgnesError(
            "curl connectivity test failed: "
            + (completed.stderr.strip() or f"curl exit code {completed.returncode}")
        )
    result: dict[str, Any] = {
        "api_root": API_ROOT,
        "transport": TRANSPORT,
        "curl_executable": curl,
        "proxies_visible_to_python": getproxies(),
        "resolved_addresses": addresses,
        "api_key_present": bool(os.environ.get("AGNES_API_KEY", "").strip()),
        "http_status": int(completed.stdout.strip() or "0"),
    }
    print_json(result)
