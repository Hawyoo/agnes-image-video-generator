#!/usr/bin/env python3
"""Image generation and editing commands."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agnes_core import (
    API_ROOT, IMAGE_MODEL, TRANSPORT, AgnesError, download, image_value,
    print_json, request_json, write_base64,
)

def run_image(args: argparse.Namespace) -> None:
    extra: dict[str, Any] = {"response_format": args.response_format}
    if args.input:
        extra["image"] = [image_value(item) for item in args.input]
    body = {
        "model": IMAGE_MODEL,
        "prompt": args.prompt,
        "size": args.size,
        "extra_body": extra,
    }
    result = request_json(
        "POST",
        f"{API_ROOT}/v1/images/generations",
        body,
        timeout=args.timeout,
        retries=args.retries,
        operation="image generation",
    )
    items = result.get("data")
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise AgnesError(
            f"Image response has no result item: {json.dumps(result, ensure_ascii=False)}"
        )
    item = items[0]

    result_url = str(item["url"]) if item.get("url") else None
    if result_url:
        # Emit the useful result immediately. A later download failure must not hide it.
        print(f"agnes: image generated; url={result_url}", file=sys.stderr, flush=True)
    elif item.get("b64_json"):
        print("agnes: image generated as Base64", file=sys.stderr, flush=True)

    saved: Path | None = None
    if args.output:
        if result_url:
            try:
                saved = download(result_url, args.output, args.timeout, args.retries)
            except AgnesError as exc:
                raise AgnesError(
                    f"Image was generated but download failed; url={result_url}; {exc}"
                ) from None
        elif item.get("b64_json"):
            saved = write_base64(str(item["b64_json"]), args.output)
        else:
            raise AgnesError("Image result contained neither url nor b64_json.")

    summary = {
        "model": IMAGE_MODEL,
        "created": result.get("created"),
        "size": args.size,
        "url": result_url,
        "output": str(saved) if saved else None,
        "revised_prompt": item.get("revised_prompt"),
        "response_format": args.response_format,
        "transport": TRANSPORT,
    }
    if args.response_format == "b64_json" and not args.output:
        summary["note"] = (
            "Base64 received but omitted from terminal output; "
            "rerun with --output to save it."
        )
    print_json(summary)
