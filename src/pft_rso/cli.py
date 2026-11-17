"""Command-line interface for local, batch PFT detection."""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
import sys

import cv2

from . import __version__
from .config import DetectorConfig
from .detector import detect_sequence
from .io import check_output_directory, load_sequence, write_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect moving-object candidates using median-background proximity filtering and tracking."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--input", type=Path, required=True, help="Directory of single-frame images in temporal filename order")
    parser.add_argument("--output", type=Path, required=True, help="New or empty directory for local results")
    parser.add_argument("--config", type=Path, help="JSON parameter object; explicit CLI flags override its values")
    parser.add_argument("--save-overlays", action="store_true", help="Also write annotated PNGs locally")
    parser.add_argument("--threshold", type=int, help="Normalized foreground intensity must be > this value (default: 1)")
    parser.add_argument("--median-window", type=int, help="Frames per median block (default: 30)")
    parser.add_argument("--min-area", type=float, help="Inclusive minimum contour area in px^2 (default: 0)")
    parser.add_argument("--max-area", type=float, help="Exclusive maximum contour area in px^2 (default: 50)")
    parser.add_argument("--star-radius", type=float, help="Exclusive background proximity radius in pixels (default: 6)")
    parser.add_argument("--match-radius", type=float, help="Exclusive candidate association radius in pixels (default: 20)")
    parser.add_argument("--star-match-radius", type=float, help="Exclusive star-like association radius in pixels (default: 5)")
    parser.add_argument("--min-displacement", type=float, help="Track endpoint displacement must exceed this many pixels (default: 8)")
    parser.add_argument("--min-track-length", type=int, help="Minimum candidate observations per retained track (default: 2)")
    return parser


def configuration(args: argparse.Namespace) -> DetectorConfig:
    values = {}
    valid = {field.name for field in fields(DetectorConfig)}
    if args.config is not None:
        values = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(values, dict):
            raise ValueError("Configuration must be a JSON object")
        unknown = set(values) - valid
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
    for name in valid:
        value = getattr(args, name, None)
        if value is not None:
            values[name] = value
    return DetectorConfig(**values)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = configuration(args)
        check_output_directory(args.output)
        paths, frames = load_sequence(args.input, config)
        result = detect_sequence(frames, config)
        output = write_results(result, paths, args.output, save_overlays=args.save_overlays)
    except (OSError, ValueError, TypeError, cv2.error) as error:
        print(f"pft-detect: {error}", file=sys.stderr)
        return 2
    tracks = len({d.object_id for d in result.rsos})
    print(f"Processed {result.frame_count} frames: {len(result.rsos)} RSO-candidate observations in {tracks} tracks.")
    print(f"Saved results to {output}")
    return 0

