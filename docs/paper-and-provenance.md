# Paper and code provenance

## Associated publication

Vithurshan Suthakar, Mishal Vellani, Emilee Brown, Aiden Sanvido, and Regina S.K.
Lee. **ORBIT: Open-Source Research for Better Identification and Tracking of Space
Objects.** 18th International Conference on Space Operations, Montreal, Canada,
26–30 May 2025. SpaceOps-2025, paper ID 509, 11 pages.

These details were taken from the supplied `SpaceOps2025_0509.pdf`, page 1. No DOI
was supplied or inferred. The PDF is not redistributed in this repository.

The most relevant sections are:

- Section 2.2, pages 5–6: PFT+ detection method and Figures 3–4.
- Section 2.4, pages 7–8: dataset context.
- Section 3, pages 8–9: evaluation description and Figure 7.

The paper covers the wider ORBIT web platform and annotation workflow. This
repository contains the standalone detection component derived from the supplied
ModifiedPFT scripts; it does not contain that platform.

## Source attribution

The supplied archive contained `main.py` and `score_calculation.py`, alongside
images, CSV data, an output video, and IDE files. The header in `main.py` credits
**Aiden Sanvido (2023-07)**. That attribution is retained. The publication's author
list describes the paper and is not an independent determination of software
authorship or ownership.

Unmodified copies of the two original scripts are retained as non-executable
`.py.txt` reference files in [legacy](../legacy/). Input images, original CSV data,
video, and IDE files are excluded. No release tag, commit identifier, or dependency
lockfile was supplied to establish the exact relationship between this archive
and the code evaluated in the paper.

The maintained package corrects implementation issues and adds configuration,
structured outputs, and a command-line interface. It should not be described as
bit-for-bit or result-for-result identical to the supplied scripts.

## Relationship between versions

| Feature | Paper description | Uploaded scripts | Maintained package |
|---|---|---|---|
| Preprocessing | 8-bit grayscale normalization and thresholding (§2.2, p.5). | Default OpenCV color decoding; normalization and thresholding precede grayscale conversion. | Preserves native 8/16-bit grayscale values until normalization; converts color to grayscale before normalization. This changes preprocessing behavior. |
| Background model | Segment median; rolling updates (§2.2, pp.5–6). | Fixed 30-frame block updates; final frame excluded from the last median, with boundary/indexing defects. | Configurable segment median; includes all frames and aligns each frame to its segment. |
| Background suppression | Called “Median Frame Differencing”; prose describes comparing detections with median-source positions (§2.2, p.5). | Spatial proximity exclusion; no pixel-wise subtraction. | Spatial proximity exclusion, documented explicitly. |
| Tracking | Proximity and motion direction; predicted-trajectory re-identification after gaps (§2.2, p.5). | Greedy previous-frame proximity only; delayed association and a star-match consumption bug. | Previous-frame proximity with corrected association and one-use matching; no direction model or gap bridging. |
| Final candidate filtering | Not specified in detail in §2.2. | At least two observations and net displacement >8 pixels; singleton candidates discarded. | Configurable length and net-displacement checks; short candidates remain inspectable as rejected observations. |
| Outputs | Coordinates, ID, bounding-box size, brightness, CSVs and annotated PNGs (§2.2, pp.5–6). | Four-column position/ID CSVs and an OpenCV text-label preview. | Structured detection metadata including bounding boxes and contour area; legacy-compatible CSV export; optional local overlays. No brightness estimate. |
| Application | Web platform and manual annotation tool (§2, pp.3–7). | Standalone scripts. | Headless command-line detector and Python API. |

Differences in this table concern the supplied archive. They do not establish
which features were present in any separate ORBIT implementation used by the
authors. The [algorithm documentation](algorithm.md) describes the maintained
package's behavior.

## Evaluation status

The paper reports RSO precision of 98%, recall of 76%, and F1 of 86% in its
abstract (page 1) and Section 3 (page 9). These are **published results, not
independently reproduced measurements for this package**. Do not use them as a
validated benchmark for the refactored release or for a different dataset.

The uploaded `score_calculation.py` is preserved only as legacy reference. Its
records are stored as `[frame, x, y]`, but matching compares the frame and x
entries instead of x and y. It also permits multiple matches to the same
annotation, excludes the last ground-truth frame, and does not handle empty data
or zero metric denominators. It is not part of the executable package and should
not be used to calculate scientific performance metrics.

A new benchmark requires a documented dataset, frame alignment, independent
annotations, a stated spatial matching rule, one-to-one matching, and a recorded
code/configuration version. Synthetic functional checks can verify program
behavior; they cannot establish detection accuracy on real observations.

## Licensing

The uploaded source did not include a software license. The paper's description
of ORBIT as open source does not specify the terms for this code. A software
license must be selected by the appropriate rights holders before the repository
can state that redistribution and reuse are permitted under that license.
