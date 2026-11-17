"""PFT-based resident-space-object candidate detection."""

from .config import DetectorConfig
from .detector import Detection, DetectionResult, detect_sequence, preprocess_frame

__version__ = "0.1.0"

__all__ = [
    "Detection", "DetectionResult", "DetectorConfig", "detect_sequence",
    "preprocess_frame", "__version__",
]
