# Usage and output reference

## Prepare an input sequence

Use one chronological sequence of equal-sized frames per run. Put local frames in
`data/my-sequence/` or point the CLI at a directory elsewhere on your computer.
The loader ignores unsupported extensions and reads supported files directly in
the directory. A supported but unreadable image is an error; it is not silently
skipped, because skipping frames changes association.

Natural sorting treats digit groups numerically. Rename files if their names do
not represent time order. Timestamps and EXIF acquisition times are not parsed.
Check `frames.csv` before comparing results with annotations. The first file in
that manifest is frame 0, including when the original filenames start at 1.

Grayscale images are the intended input. Color inputs are converted using OpenCV's
BGR/BGRA-to-grayscale conversion; alpha is not used as a mask. Eight-bit and
16-bit unsigned images are supported. FITS, floats, and TIFF stacks require a
separate conversion step. Per-frame normalization changes the intensity scale;
outputs are not calibrated photometry.

## Run with reproducible parameters

```bash
pft-detect --input data/my-sequence --output outputs/run-001 --config config/default.json
```

Unspecified configuration keys take their defaults. Explicit CLI flags override
the JSON configuration. Unknown keys, nonfinite numbers, noninteger frame counts,
and invalid ranges fail with an error. Output must be a new or empty directory.
This prevents an accidental rerun from overwriting earlier results.

To create local visualizations:

```bash
pft-detect --input data/my-sequence --output outputs/run-002 --save-overlays
```

Overlays use red boxes for retained RSO candidates and blue boxes for star-like
observations. The displayed box has three pixels of padding; exported bounding
rectangles describe the actual detected contour. Short rejected tracks are not
drawn. Overlay filenames use the zero-based frame index, not the input filename.

No GUI, account, network connection, model weights, GPU, or dataset download is
needed at runtime. NumPy and the headless OpenCV package are the runtime dependencies.
Use a clean environment: OpenCV's wheel maintainers advise installing only one
OpenCV Python distribution because the variants share the `cv2` namespace.
See the [official package instructions](https://pypi.org/project/opencv-python-headless/).

## Choosing parameters

Start by examining several normalized frames and their detections. Parameter
effects follow the algorithm's rules; they are not validated accuracy guarantees.

| Symptom | Setting or assumption to inspect |
| --- | --- |
| Large numbers of noise contours | Increase `threshold` cautiously; the inherited value 1 is low. A higher value can also remove faint targets. |
| Large bright blobs accepted | Reduce `max_area`. It is contour area, so thin structures can still have small area. |
| Isolated point noise accepted | Consider `min_area > 0`; this also removes legitimate one-pixel targets. |
| Stars drift out of their exclusion regions | Inspect registration and the median-block length, then assess `star_radius`. A larger radius can suppress targets passing close to stars. |
| Fast objects fragment | Compare per-frame motion with `match_radius`. A larger radius also makes incorrect matches easier in crowded fields. |
| Slow candidates removed | Inspect `min_displacement` and sequence length. The test uses endpoint separation, not total path length. |
| Very brief tracks removed | Inspect `min_track_length`; its minimum is 2. |
| Last few frames change classification | Inspect the short final median block. One-frame blocks treat every foreground source as persistent. |

The frame interval is not a parameter. Association uses pixels per successive
frame, not pixels per second. Irregular cadence and missing frames therefore need
careful interpretation. Rapid attitude motion is outside the stable-background
assumption; this release does not register images or estimate platform attitude.

The median is computed separately for frames 0-29, 30-59, and so on under defaults.
A block may contain fewer frames at the end. For even block lengths, a pixel bright
in exactly half the frames can produce median intensity 127, which is still
foreground for contour extraction. A slowly moving object can consequently be
included in the background reference.

## Output schemas

### Four-column tables

`frame_data.csv`, `star_data.csv`, and `rejected_data.csv` have:

```text
Frame,Object ID,X-Coordinate,Y-Coordinate
```

`Frame` is the zero-based manifest index. `Object ID` is a positive integer scoped
to this run. `X-Coordinate` and `Y-Coordinate` are integer centers of axis-aligned
bounding rectangles, in pixels. Empty results still contain the header.

The column names match the original script, but the corrected frame indexing and
tracking mean the values are not guaranteed to match its output. Do not apply the
old script's implicit one-frame shift to the new output.

### Detailed table

`detections.csv` contains one row per retained, background, or short-track
observation after contour-size filtering:

| Field | Meaning |
| --- | --- |
| `class` | `rso_candidate`, `star_like`, or `short_track` |
| `filename` | Input basename corresponding to `frame` |
| `frame` | Zero-based input-frame index |
| `object_id` | Run-local track ID |
| `x`, `y` | Integer bounding-rectangle center |
| `bbox_x`, `bbox_y` | Top-left corner of the contour bounding rectangle |
| `width`, `height` | Rectangle dimensions in pixels |
| `contour_area` | OpenCV geometric contour area in pixels² |

`star_like` combines detections close to median-reference sources and sufficiently
long candidate tracks that fail the endpoint-displacement test. It is not a
catalogue of verified stars. `short_track` contains candidate observations removed
by the minimum-length test. Contours excluded by size are not recorded.

The rectangle covers `bbox_x <= x_pixel < bbox_x + width` and the equivalent range
in y. There is no intensity-weighted centroid, brightness, uncertainty, right
ascension/declination, timestamp, or orbit association in these outputs.

### Run metadata

`frames.csv` maps each frame index to its input basename. `run.json` records the
software and runtime versions, parameters, image dimensions, counts, and overlay
request. Counts distinguish observations from unique retained IDs. They do not
estimate precision, recall, or the number of distinct physical objects.

Only input basenames are recorded; machine-specific absolute paths are not written
to the metadata. Treat generated results as local data and keep them out of Git.

## Python arrays

```python
import numpy as np
from pft_rso import DetectorConfig, preprocess_frame, detect_sequence

config = DetectorConfig()
raw_frames = [np.zeros((64, 64), dtype=np.uint16) for _ in range(3)]
binary_frames = [preprocess_frame(frame, config) for frame in raw_frames]
result = detect_sequence(binary_frames, config)
assert result.frame_count == 3
assert result.rsos == []
```

Pass a sequence with length and slicing support, such as a list or an `N x H x W`
NumPy array of binary frames. The API does not consume generators. It does not
mutate input arrays. Use `result.rsos`, `result.stars`, and `result.rejected` to
inspect individual `Detection` records.

## Troubleshooting

| Error or observation | Action |
| --- | --- |
| `pft-detect` is not found | Activate the environment used for installation, or run `python -m pft_rso`. |
| Cannot import `cv2` | Install the package in the active environment with `python -m pip install -e .`. |
| No supported images found | Check the directory, extension, and whether files are inside an extra nested folder. |
| Cannot decode image | Check that the image is valid and supported; convert it separately if needed. |
| Image dimensions differ | Run separate sequences or prepare equal-sized frames before detection. |
| Output must be new or empty | Choose another run directory to preserve the previous results. |
| No retained RSO candidates | This can be a valid result. Check sequence length, image contrast, foreground threshold, median contamination, and motion thresholds. |

