"""Local image loading and explicit result export; no network operations."""

from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path
import platform
import re
from typing import Sequence

import cv2
import numpy as np

from . import __version__
from .config import DetectorConfig
from .detector import Detection, DetectionResult, preprocess_frame


IMAGE_EXTENSIONS = frozenset({".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"})
LEGACY_COLUMNS = ["Frame", "Object ID", "X-Coordinate", "Y-Coordinate"]


def natural_key(path: Path) -> tuple:
    """Order frame2 before frame10, with a stable filename tie-breaker."""
    tokens = tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )
    return tokens, path.name


def discover_images(directory: str | Path) -> list[Path]:
    """Find supported single-frame images directly inside a directory."""
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Input directory does not exist: {directory}")
    paths = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        key=natural_key,
    )
    if not paths:
        raise ValueError(f"No supported images found in {directory}")
    return paths


def read_image(path: str | Path) -> np.ndarray:
    """Decode without discarding native bit depth; reject multipage TIFFs."""
    path = Path(path)
    if path.suffix.lower() in {".tif", ".tiff"} and cv2.imcount(str(path)) > 1:
        raise ValueError(f"Multipage TIFF is unsupported; export one frame per file: {path.name}")
    # imdecode also supports paths containing non-ASCII characters on Windows.
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Cannot decode image: {path.name}")
    return image


def load_sequence(
    directory: str | Path, config: DetectorConfig | None = None
) -> tuple[list[Path], list[np.ndarray]]:
    """Load naturally sorted files and return their aligned binary frames."""
    config = config or DetectorConfig()
    paths = discover_images(directory)
    frames = []
    shape = None
    for path in paths:
        try:
            frame = preprocess_frame(read_image(path), config)
        except (ValueError, TypeError, cv2.error) as error:
            raise ValueError(f"Invalid image {path.name}: {error}") from error
        if shape is not None and frame.shape != shape:
            raise ValueError(f"Image dimensions differ: {path.name} is {frame.shape}, expected {shape}")
        shape = frame.shape
        frames.append(frame)
    return paths, frames


def check_output_directory(directory: str | Path) -> Path:
    """Refuse to overwrite an existing nonempty location."""
    directory = Path(directory)
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"Output must be a new or empty directory: {directory}")
    return directory


def _write_legacy_csv(path: Path, detections: Sequence[Detection]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(LEGACY_COLUMNS)
        writer.writerows((d.frame, d.object_id, d.x, d.y) for d in detections)


def write_results(
    result: DetectionResult,
    paths: Sequence[Path],
    directory: str | Path,
    *,
    save_overlays: bool = False,
) -> Path:
    """Write CSVs, frame order, parameters and optional local PNG overlays.

    File paths in exported tables contain basenames only. No source image is
    copied; overlays are generated only when explicitly requested.
    """
    if len(paths) != result.frame_count:
        raise ValueError("Filename count does not match result.frame_count")
    directory = check_output_directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    _write_legacy_csv(directory / "frame_data.csv", result.rsos)
    _write_legacy_csv(directory / "star_data.csv", result.stars)
    _write_legacy_csv(directory / "rejected_data.csv", result.rejected)

    with (directory / "frames.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "filename"])
        writer.writerows((index, Path(path).name) for index, path in enumerate(paths))

    rows = []
    for label, detections in (
        ("rso_candidate", result.rsos),
        ("star_like", result.stars),
        ("short_track", result.rejected),
    ):
        for detection in detections:
            rows.append({
                "class": label,
                "filename": Path(paths[detection.frame]).name,
                **asdict(detection),
            })
    rows.sort(key=lambda row: (row["frame"], row["object_id"]))
    columns = ["class", "filename", "frame", "object_id", "x", "y", "bbox_x", "bbox_y", "width", "height", "contour_area"]
    with (directory / "detections.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "schema_version": 1,
        "software": {"name": "pft-rso-detection", "version": __version__},
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "opencv": cv2.__version__},
        "frame_count": result.frame_count,
        "frame_index_base": 0,
        "image_shape_hw": list(result.image_shape),
        "ordering": "natural filename order; see frames.csv",
        "parameters": asdict(result.config),
        "counts": {
            "rso_observations": len(result.rsos),
            "rso_tracks": len({d.object_id for d in result.rsos}),
            "star_like_observations": len(result.stars),
            "short_track_observations": len(result.rejected),
        },
        "overlays_requested": save_overlays,
    }
    if save_overlays:
        _write_overlays(result, paths, directory / "overlays")
    (directory / "run.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return directory


def _write_overlays(result: DetectionResult, paths: Sequence[Path], directory: Path) -> None:
    """Draw RSO candidates in red and background/star-like detections in blue."""
    by_frame: dict[int, list[tuple[Detection, tuple[int, int, int]]]] = {}
    for detections, color in ((result.stars, (255, 110, 30)), (result.rsos, (30, 30, 255))):
        for detection in detections:
            by_frame.setdefault(detection.frame, []).append((detection, color))
    directory.mkdir()
    for index, path in enumerate(paths):
        image = read_image(path)
        if image.ndim == 3:
            conversion = cv2.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv2.COLOR_BGR2GRAY
            image = cv2.cvtColor(image, conversion)
        image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        height, width = image.shape[:2]
        for d, color in by_frame.get(index, []):
            start = (max(0, d.bbox_x - 3), max(0, d.bbox_y - 3))
            end = (min(width - 1, d.bbox_x + d.width + 2), min(height - 1, d.bbox_y + d.height + 2))
            cv2.rectangle(image, start, end, color, 1)
            cv2.putText(image, str(d.object_id), (start[0], max(10, start[1] - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
        success, encoded = cv2.imencode(".png", image)
        if not success:
            raise OSError(f"Could not encode overlay for frame {index}")
        encoded.tofile(directory / f"frame_{index:06d}.png")

