"""Parameters for the ModifiedPFT proximity detector."""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Integral, Real


@dataclass(frozen=True, slots=True)
class DetectorConfig:
    """Pixel-space thresholds, with the supplied research script's defaults.

    Contours pass when ``min_area <= area < max_area``. Proximity and
    association use strict distance limits. A candidate track is accepted only
    when its endpoint displacement is strictly greater than ``min_displacement``.
    ``median_window`` specifies a nonoverlapping block length, not a sliding
    window. No parameter is expressed in angular or physical units.
    """

    threshold: int = 1
    median_window: int = 30
    min_area: float = 0.0
    max_area: float = 50.0
    star_radius: float = 6.0
    match_radius: float = 20.0
    star_match_radius: float = 5.0
    min_displacement: float = 8.0
    min_track_length: int = 2

    def __post_init__(self) -> None:
        for name, lower, upper in (
            ("threshold", 0, 255),
            ("median_window", 1, None),
            ("min_track_length", 2, None),
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral):
                raise ValueError(f"{name} must be an integer")
            if value < lower or (upper is not None and value > upper):
                limit = f"between {lower} and {upper}" if upper is not None else f"at least {lower}"
                raise ValueError(f"{name} must be {limit}")
            object.__setattr__(self, name, int(value))

        for name in (
            "min_area", "max_area", "star_radius", "match_radius",
            "star_match_radius", "min_displacement",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
            if value < 0 or (name not in {"min_area", "min_displacement"} and value == 0):
                limit = "nonnegative" if name in {"min_area", "min_displacement"} else "positive"
                raise ValueError(f"{name} must be {limit}")
            object.__setattr__(self, name, float(value))

        if self.max_area <= self.min_area:
            raise ValueError("max_area must be greater than min_area")
