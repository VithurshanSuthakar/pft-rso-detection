# PFT RSO Detection

**Proximity filtering and tracking for moving-object candidates in optical image sequences.**

This repository provides a standalone Python implementation of the **ModifiedPFT**
detector associated with the PFT+ method in the SpaceOps 2025 ORBIT paper. It uses
segment-wise median backgrounds to identify persistent sources, filters nearby
contours, links moving candidates between consecutive frames, and retains tracks
with sufficient net displacement.

The release focuses on detection and tracking. The ORBIT web platform and manual
annotation interface described in the paper are separate components.

## Quick start

Use Python 3.10 or later. Create an environment in the repository directory:

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Or in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the package, generate a small synthetic sequence, and run the detector:

```bash
python -m pip install -e .
python examples/make_synthetic.py --output data/synthetic
pft-detect --input data/synthetic --output outputs/demo --save-overlays
```

The example creates 48 toy frames locally. It illustrates installation and the
output format; it is not an astronomical performance benchmark. Generated frames
and results are ignored by Git. Use a new output directory when running again.

For your own images:

```bash
pft-detect --input /path/to/frames --output outputs/my-sequence
```

`python -m pft_rso` is equivalent to `pft-detect`. Run `pft-detect --help` to see
all options. Nothing is uploaded by the detector.

## Input

- One image per file: TIFF, PNG, JPEG, or BMP, with 8-bit or 16-bit unsigned
  grayscale values, or supported BGR/BGRA color data.
- All frames must have the same dimensions. Images are read from the specified
  directory only, without descending into subdirectories.
- Filenames must encode chronological order. Natural sorting places `frame2.tif`
  before `frame10.tif`; the exact order is recorded in `frames.csv`.
- Each frame is converted to grayscale if necessary, normalized to 0-255, then
  thresholded. Native 16-bit values are preserved until normalization.
- FITS files, floating-point images, videos, and multipage TIFFs are not supported
  by this release. Convert these to separate supported images first.

The method is intended for relatively stable star fields containing small moving
sources. It uses future images within each median block and processes the sequence
in memory, so it is an offline batch detector.

## What the detector does

1. **Normalize and threshold** each frame to obtain foreground contours.
2. **Construct a median reference** for each block of 30 frames by default.
3. **Filter by size and proximity** to median-reference sources.
4. **Associate candidates** with the nearest available detection in the previous
   frame, using a pixel-distance threshold.
5. **Retain moving tracks** with at least two observations and more than eight
   pixels of first-to-last displacement.

The filtering uses distances to median-contour centers. There is no pixel-wise
frame subtraction in this implementation. Tracking is greedy and uses only the
previous frame; it does not predict trajectories or bridge missed detections.

Outputs are **RSO candidates** and **star-like/background detections**. These
labels describe the algorithm's decisions, not independently verified identities.

## Outputs

| File | Contents |
| --- | --- |
| `frame_data.csv` | Retained RSO-candidate observations, using the original four column names |
| `star_data.csv` | Background/star-like observations, including low-displacement candidate tracks |
| `rejected_data.csv` | Candidate observations from tracks shorter than the configured minimum length |
| `detections.csv` | Combined records with class, filename, bounding rectangle, and contour area |
| `frames.csv` | Exact mapping from zero-based frame indices to input filenames |
| `run.json` | Parameters, dimensions, observation/track counts, and runtime versions |
| `overlays/` | Optional annotated PNGs, created only with `--save-overlays` |

Frame indices are zero-based and aligned to the input manifest. Pixel coordinates
use the top-left origin: `x` increases rightward and `y` downward. Locations are
integer bounding-rectangle centers. IDs are local to a run and may fragment when
an object is missed or switches classification.

## Parameters

The defaults retain the numeric thresholds of the supplied source.

| CLI flag | Default | Rule |
| --- | ---: | --- |
| `--threshold` | 1 | Normalized intensity must be **greater than** this integer |
| `--median-window` | 30 | Frames in each nonoverlapping median block |
| `--min-area` | 0 | Contour area must be **at least** this many pixels² |
| `--max-area` | 50 | Contour area must be **less than** this many pixels² |
| `--star-radius` | 6 | Background proximity distance must be **less than** this many pixels |
| `--match-radius` | 20 | Consecutive candidate displacement must be **less than** this many pixels |
| `--star-match-radius` | 5 | Consecutive star-like displacement must be **less than** this many pixels |
| `--min-displacement` | 8 | Candidate track endpoint displacement must be **greater than** this many pixels |
| `--min-track-length` | 2 | Minimum number of observations in a candidate track |

Contour area is geometric contour area, not the number of bright pixels or the
bounding-box area. Single-pixel contours can have zero area and pass the defaults.

Use a configuration file and optionally override selected values:

```bash
pft-detect --input /path/to/frames --output outputs/tuned --config config/default.json --threshold 10
```

Thresholds are in image pixels and must be assessed for each sensor, cadence, and
background. The default intensity threshold is low and can admit noise in raw
images. See [usage and tuning](docs/usage.md) before interpreting detections.

## Python API

```python
from pft_rso import DetectorConfig, detect_sequence
from pft_rso.io import load_sequence, write_results

config = DetectorConfig(median_window=30, threshold=1)
paths, binary_frames = load_sequence("/path/to/frames", config)
result = detect_sequence(binary_frames, config)
write_results(result, paths, "outputs/api-run")

print(len(result.rsos), "retained observations")
print(len({d.object_id for d in result.rsos}), "tracks")
```

For arrays loaded elsewhere, use `preprocess_frame(image, config)` first.
`detect_sequence` accepts equally sized, two-dimensional `uint8` arrays containing
only 0 and 255. All parameters used for preprocessing should match the detector
configuration recorded with the results.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Algorithm](docs/algorithm.md) | Detection stages, exact rules, and limitations |
| [Usage](docs/usage.md) | Input preparation, settings, output schemas, and troubleshooting |
| [Changes from the supplied source](docs/changes-from-source.md) | Corrections and behavior changes |
| [Paper and provenance](docs/paper-and-provenance.md) | Relationship to the publication and original implementation |
| [GitHub setup](docs/github-setup.md) | Create the repository and push only source/documentation |
| [Validation](docs/validation.md) | Checks performed and the limits of verification |

## Tests and data exclusion

```bash
python -m unittest discover -s tests -v
```

Tests generate their inputs in memory or temporary directories. No input images,
original CSVs, videos, or paper PDFs are distributed. Before pushing, stage the
intended files and check the staged contents:

```bash
git add .
python tools/check_repository.py
git diff --cached --stat
```

The check rejects non-source formats, binary content, and data/output directories,
including files forcibly staged despite `.gitignore`. GitHub Actions runs the
synthetic tests and repository check on pushes and pull requests.

## Associated publication

V. Suthakar, M. Vellani, E. Brown, A. Sanvido, and R. S. K. Lee,
**“ORBIT: Open-Source Research for Better Identification and Tracking of Space
Objects,”** 18th International Conference on Space Operations, Montreal, Canada,
26-30 May 2025, paper ID 509.

The method is discussed in Section 2.2, pp. 5-6. Bibliographic records are supplied
in [CITATION.cff](CITATION.cff) and [references.bib](references.bib). No DOI was
present in the supplied paper.

This is a cleaned and corrected implementation of the supplied archive. It is
not a verified reproduction of the paper's evaluated release. Published scores
are described, with their scope, in the [provenance guide](docs/paper-and-provenance.md).

## Attribution and license status

The supplied detector credits **Aiden Sanvido (2023-07)**. That credit is preserved
in the implementation and [original source snapshots](legacy/README.md).

No software license was included in the supplied archive, and this preparation
does not assign one. A license remains to be selected by the appropriate rights
holders. See [NOTICE.md](NOTICE.md).

