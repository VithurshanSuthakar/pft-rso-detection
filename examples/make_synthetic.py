"""Generate a small toy sequence locally; no observational data is distributed.

The example contains fixed point sources, one translating point source, and one
single-frame artifact. It checks installation and illustrates output only; it is
not a physical sensor simulation or a scientific performance benchmark.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def generate(directory: Path) -> None:
    if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError(f"Use a new or empty directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    for index in range(48):
        frame = rng.integers(1000, 1008, size=(128, 128), dtype=np.uint16)
        for position in ((20, 18), (100, 100), (95, 20)):
            cv2.circle(frame, position, 1, 60000, -1)
        cv2.circle(frame, (10 + 2 * index, 65), 1, 40000, -1)
        if index == 17:
            frame[40, 70] = 60000
        success, encoded = cv2.imencode(".tif", frame)
        if not success:
            raise OSError("Could not encode synthetic frame")
        encoded.tofile(directory / f"frame_{index:04d}.tif")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/synthetic"))
    args = parser.parse_args()
    try:
        generate(args.output)
    except (OSError, ValueError, cv2.error) as error:
        parser.exit(2, f"make_synthetic: {error}\n")
    print(f"Created 48 synthetic frames in {args.output}")

