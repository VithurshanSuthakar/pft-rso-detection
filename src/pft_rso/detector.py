"""Median-background proximity filtering and previous-frame association.

Derived from the supplied ModifiedPFT research script, credited there to
Aiden Sanvido (2023-07). This module retains its detection rules while fixing
frame alignment, median block boundaries, and one-to-one star association.
It performs no image subtraction, motion prediction, or gap recovery.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

import cv2
import numpy as np

from .config import DetectorConfig


@dataclass(frozen=True, slots=True)
class Detection:
    """One observation, in zero-based input-frame and pixel coordinates.

    ``x`` and ``y`` are integer bounding-rectangle centers, not intensity
    centroids. ``contour_area`` is OpenCV's geometric contour area, which can
    be zero for single-pixel or line-like contours.
    """

    frame: int
    object_id: int
    x: int
    y: int
    bbox_x: int
    bbox_y: int
    width: int
    height: int
    contour_area: float


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Sequence results, ordered by frame and then object ID.

    ``rsos`` contains candidate observations surviving the final track filter.
    ``stars`` combines median-proximity detections with sufficiently long
    candidate tracks failing the endpoint-displacement filter. These are
    algorithmic categories, not verified physical identities. ``rejected``
    contains candidate observations in tracks shorter than ``min_track_length``.
    """

    rsos: list[Detection]
    stars: list[Detection]
    rejected: list[Detection]
    frame_count: int
    image_shape: tuple[int, int]
    config: DetectorConfig


def _config_or_default(config: DetectorConfig | None) -> DetectorConfig:
    if config is None:
        return DetectorConfig()
    if not isinstance(config, DetectorConfig):
        raise TypeError("config must be a DetectorConfig")
    return config


def preprocess_frame(
    image: np.ndarray, config: DetectorConfig | None = None,
) -> np.ndarray:
    """Convert uint8/uint16 grayscale or BGR/BGRA input into a binary frame.

    Color is converted to grayscale before per-frame min-max normalization
    into uint8. Pixels strictly above ``config.threshold`` become 255; all
    others become zero. Constant frames become entirely zero. The input
    array is not modified. Input intensities are not photometrically calibrated.
    """
    config = _config_or_default(config)
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    if image.dtype not in (np.dtype("uint8"), np.dtype("uint16")):
        raise ValueError("image must have uint8 or uint16 dtype")
    if image.size == 0:
        raise ValueError("image must not be empty")

    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] in (3, 4):
        conversion = cv2.COLOR_BGR2GRAY if image.shape[2] == 3 else cv2.COLOR_BGRA2GRAY
        gray = cv2.cvtColor(image, conversion)
    else:
        raise ValueError("image must be 2D grayscale or have 3 BGR / 4 BGRA channels")

    normalized = cv2.normalize(
        gray, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U,
    )
    _, binary = cv2.threshold(normalized, config.threshold, 255, cv2.THRESH_BINARY)
    return binary


def _validate_frames(frames: Sequence[np.ndarray]) -> tuple[int, int]:
    if len(frames) == 0:
        raise ValueError("at least one binary frame is required")
    shape: tuple[int, int] | None = None
    for index, frame in enumerate(frames):
        if not isinstance(frame, np.ndarray):
            raise TypeError(f"frame {index} must be a NumPy array")
        if frame.ndim != 2 or frame.dtype != np.uint8 or frame.size == 0:
            raise ValueError(f"frame {index} must be a nonempty 2D uint8 array")
        if shape is None:
            shape = (int(frame.shape[0]), int(frame.shape[1]))
        elif frame.shape != shape:
            raise ValueError(f"frame {index} has shape {frame.shape}; expected {shape}")
        if np.any((frame != 0) & (frame != 255)):
            raise ValueError(f"frame {index} is not binary (expected only 0 and 255)")
    assert shape is not None
    return shape


def _contours(frame: np.ndarray) -> tuple[np.ndarray, ...]:
    contours, _ = cv2.findContours(frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return tuple(contours)


def _center(contour: np.ndarray) -> tuple[int, int]:
    x, y, width, height = cv2.boundingRect(contour)
    return x + width // 2, y + height // 2


def _match_previous(
    previous: dict[int, Detection], x: int, y: int, radius: float,
) -> int | None:
    """Consume the nearest eligible previous observation, breaking ties by ID."""
    if not previous:
        return None
    distance, object_id = min(
        ((obs.x - x) ** 2 + (obs.y - y) ** 2, object_id)
        for object_id, obs in previous.items()
    )
    if math.sqrt(distance) < radius:
        previous.pop(object_id)
        return object_id
    return None


def detect_sequence(
    frames: Sequence[np.ndarray], config: DetectorConfig | None = None,
) -> DetectionResult:
    """Detect moving candidates in an ordered sequence of binary frames.

    Supply same-sized 2D uint8 frames containing only 0 and 255, usually from
    :func:`preprocess_frame`. Every input frame is processed, including frame
    zero and the final frame. Star-reference contours are computed from the
    median of each nonoverlapping block, including a shorter final block.

    Median contours are used as proximity references, never subtracted from
    the current frame. Matching is greedy in OpenCV contour order and uses
    only the immediately preceding frame, separately for stars and candidates.
    IDs are unique across both categories. A missed detection or category
    change can break a track. All frames are held in memory; the median uses
    future frames within its block, so this is an offline method.
    """
    config = _config_or_default(config)
    image_shape = _validate_frames(frames)
    previous_candidates: dict[int, Detection] = {}
    previous_stars: dict[int, Detection] = {}
    candidate_tracks: dict[int, list[Detection]] = {}
    stars: list[Detection] = []
    next_id = 1
    median_centers: list[tuple[int, int]] = []

    for frame_index, frame in enumerate(frames):
        if frame_index % config.median_window == 0:
            stop = min(frame_index + config.median_window, len(frames))
            block = np.stack(frames[frame_index:stop], axis=0)
            median_frame = np.median(block, axis=0).astype(np.uint8)
            median_centers = [_center(contour) for contour in _contours(median_frame)]

        current_candidates: dict[int, Detection] = {}
        current_stars: dict[int, Detection] = {}
        for contour in _contours(frame):
            area = float(cv2.contourArea(contour))
            if not config.min_area <= area < config.max_area:
                continue
            bbox_x, bbox_y, width, height = cv2.boundingRect(contour)
            x, y = bbox_x + width // 2, bbox_y + height // 2
            near_star = any(
                math.hypot(x - star_x, y - star_y) < config.star_radius
                for star_x, star_y in median_centers
            )
            previous = previous_stars if near_star else previous_candidates
            radius = config.star_match_radius if near_star else config.match_radius
            object_id = _match_previous(previous, x, y, radius)
            if object_id is None:
                object_id = next_id
                next_id += 1

            detection = Detection(
                frame=frame_index, object_id=object_id, x=x, y=y,
                bbox_x=bbox_x, bbox_y=bbox_y, width=width, height=height,
                contour_area=area,
            )
            if near_star:
                current_stars[object_id] = detection
                stars.append(detection)
            else:
                current_candidates[object_id] = detection
                candidate_tracks.setdefault(object_id, []).append(detection)

        previous_candidates = current_candidates
        previous_stars = current_stars

    rsos: list[Detection] = []
    rejected: list[Detection] = []
    for track in candidate_tracks.values():
        if len(track) < config.min_track_length:
            rejected.extend(track)
        elif math.hypot(track[-1].x - track[0].x, track[-1].y - track[0].y) > config.min_displacement:
            rsos.extend(track)
        else:
            stars.extend(track)

    def chronological(observations: list[Detection]) -> list[Detection]:
        return sorted(observations, key=lambda obs: (obs.frame, obs.object_id))

    return DetectionResult(
        rsos=chronological(rsos), stars=chronological(stars),
        rejected=chronological(rejected), frame_count=len(frames),
        image_shape=image_shape, config=config,
    )
