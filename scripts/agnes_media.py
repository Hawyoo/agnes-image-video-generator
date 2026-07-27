#!/usr/bin/env python3
"""CLI entry point for Agnes Image 2.0 and Video V2.0."""
from __future__ import annotations

import argparse
import sys

from agnes_core import AgnesError, VIDEO_MODEL
from agnes_image import run_image
from agnes_video import run_diagnose, run_video, run_video_status

def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Generate images and videos with Agnes using curl transport "
            "without forcing proxy bypass or direct routing."
        )
    )
    sub = root.add_subparsers(dest="command", required=True)

    image = sub.add_parser("image", help="Generate, edit, or compose an image.")
    image.add_argument("--prompt", required=True)
    image.add_argument("--size", default="1024x1024")
    image.add_argument("--input", action="append", help="URL, Data URI, or local path; repeatable.")
    image.add_argument("--response-format", choices=("url", "b64_json"), default="url")
    image.add_argument("--output", help="Download/decode the first result to this file.")
    image.add_argument("--timeout", type=float, default=360)
    image.add_argument("--retries", type=int, default=2)
    image.set_defaults(func=run_image)

    video = sub.add_parser("video", help="Create a text, image, or keyframe video task.")
    video.add_argument("--prompt", required=True)
    video.add_argument("--image", help="Public HTTPS image URL for image-to-video.")
    video.add_argument("--keyframe", action="append", help="Public HTTPS keyframe URL; repeatable.")
    video.add_argument("--height", type=int, default=768)
    video.add_argument("--width", type=int, default=1152)
    video.add_argument("--num-frames", type=int, default=121)
    video.add_argument("--frame-rate", type=float, default=24)
    video.add_argument("--num-inference-steps", type=int)
    video.add_argument("--seed", type=int)
    video.add_argument("--negative-prompt")
    video.add_argument("--poll", action="store_true", help="Wait for completion.")
    video.add_argument("--interval", type=float, default=10)
    video.add_argument("--poll-timeout", type=float, default=1800)
    video.add_argument("--request-timeout", type=float, default=360)
    video.add_argument("--retries", type=int, default=2)
    video.add_argument("--output", help="Download the completed MP4 to this file.")
    video.set_defaults(func=run_video)

    status = sub.add_parser("video-status", help="Query or poll an existing video task.")
    status.add_argument("--video-id", required=True)
    status.add_argument("--model-name", default=VIDEO_MODEL)
    status.add_argument("--poll", action="store_true")
    status.add_argument("--interval", type=float, default=10)
    status.add_argument("--poll-timeout", type=float, default=1800)
    status.add_argument("--request-timeout", type=float, default=360)
    status.add_argument("--retries", type=int, default=2)
    status.add_argument("--output", help="Download the completed MP4 to this file.")
    status.set_defaults(func=run_video_status)

    diagnose = sub.add_parser("diagnose", help="Test curl connectivity and show visible proxy settings.")
    diagnose.add_argument("--timeout", type=float, default=30)
    diagnose.set_defaults(func=run_diagnose)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except AgnesError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr, flush=True)
        return 130
    except Exception as exc:
        # Never fail silently: unexpected errors must be visible to WorkBuddy.
        print(f"unexpected error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
