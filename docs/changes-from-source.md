# Changes from the supplied ModifiedPFT scripts

This package preserves the proximity-filtering method and inherited numeric
defaults. It is a refactor with corrections, so it can change observations, frame
numbers, and IDs. It is not a bit-for-bit reproduction of the original execution.
The original scripts are preserved as reference text in [legacy/](../legacy/).

## Detection and input corrections

| Original behavior | Packaged behavior | Consequence |
| --- | --- | --- |
| Unsorted `os.listdir()` input | Filter supported formats and natural-sort filenames | Chronological order is deterministic when filenames encode time |
| Default color decoding before thresholding | Read native uint8/uint16, convert color to grayscale, normalize explicitly to uint8, then threshold | Avoids early 16-bit truncation; color and high-bit-depth results may differ |
| First input frame skipped, later indices shifted | Process every input frame, indexed from 0 | CSV positions and optional overlays align with the manifest |
| Extra initial median-contour entry | Compute and use the current block reference directly | First frames of new blocks use the correct median |
| Final median slice omitted the last image | Include the complete final, possibly short, block | Avoids empty terminal slices at lengths 1, 31, 61, etc. |
| First two processed frames independently initialized | Match from the second frame | Preserves initial adjacent-frame continuity |
| Star association removed from the wrong list | Consume each matched previous observation once in both classes | Prevents duplicate use of a previous star ID within a frame |

These corrections are covered by focused synthetic regression tests. They do not
establish improved scientific detection accuracy without a separate evaluation.

## Interface and output changes

- Detection functions have no filesystem, GUI, or network side effects on import.
- Paths and parameters are supplied through a CLI or Python API rather than by
  editing hard-coded paths inside a script.
- Original four-column RSO and star CSV headers remain available. Additional
  tables expose the frame manifest, bounding rectangles, contour areas, and short
  candidate tracks that the original silently discarded.
- The default minimum area of zero preserves eligibility of one-pixel contours.
  A configurable minimum area and minimum track length are exposed explicitly.
- Optional overlays are written as PNGs. This is new local export functionality;
  the old script only displayed IDs in an OpenCV window.
- The unused video-writer initialization was removed. There is no video export.
- Nonempty output directories are rejected to prevent accidental overwrites.
- Parameters and Python/NumPy/OpenCV versions are saved for each run.

## Operations deliberately preserved

- Median references refresh once per nonoverlapping block, not every frame.
- Median intensities are not rethresholded before contour extraction. Nonzero
  half-occupancy pixels in even-length blocks remain foreground.
- No image subtraction is added, despite the original `frame_difference` name.
- Centers remain integer bounding-rectangle centers, not photometric centroids.
- Matching remains greedy, in OpenCV contour order, with nearest-distance ties
  broken by ID. There is no trajectory prediction or gap recovery.
- Proximity/association thresholds remain strict `<` comparisons; the final
  displacement threshold remains a strict `>` comparison.
- Tracks that are long enough but have insufficient endpoint displacement are
  included among star-like/background observations.

## Evaluation scope

The original `score_calculation.py` is preserved as text for provenance and is
not installed or invoked. It compares the wrong coordinate columns, permits
many-to-many matches, omits the final truth frame, and does not handle empty truth
or zero denominators safely. No replacement scientific evaluator or claimed
reproduction score is included in this detection-focused release.

