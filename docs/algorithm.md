# Detection algorithm

The detector follows the supplied ModifiedPFT implementation: identify persistent
sources in a median background image, exclude nearby detections, associate the
remaining candidates between adjacent frames, and retain sufficiently moving
tracks. It is a rule-based image-plane method for point-like moving objects.

The associated paper describes PFT+ in Section 2.2, pages 5–6. See
[paper and provenance](paper-and-provenance.md) for the distinction between that
description, the uploaded scripts, and this maintained implementation.

## Processing stages

1. **Prepare each frame.** Read an image, convert it to grayscale, normalize its
   intensity range to 0–255, and threshold it. Pixels strictly above `threshold`
   become 255; other pixels become zero. Native grayscale `uint8` and `uint16`
   input values are retained until normalization. All frames are processed.

2. **Construct a segment background.** Partition the sequence into consecutive
   blocks of up to `median_window` frames. Compute the pixel-wise median of each
   block's binary images and cast it to `uint8`. Use this background for every
   frame in that block, including the final partial block. Extract external
   contours from the median image to obtain persistent-source positions. This is
   a segment-wise update, not a median recomputed at every frame. It uses future
   frames within each segment and is therefore an offline method.

3. **Extract and filter detections.** Find external contours in each binary
   frame. Accept contours whose OpenCV contour area lies in the configured
   interval. For a bounding rectangle `(x, y, width, height)`, use the integer
   center `(int(x + width / 2), int(y + height / 2))`. This is a bounding-box
   center, not a brightness-weighted centroid.

4. **Apply proximity filtering.** Calculate the Euclidean distance from each
   accepted detection center to the persistent-source centers. A detection closer
   than `star_radius` to any of them enters the star-like category; otherwise, it
   enters the moving-object candidate category. No image subtraction is performed.

5. **Associate adjacent-frame observations.** Within each category, greedily
   associate a detection with the closest available observation in the immediately
   preceding frame, provided that the distance is below that category's matching
   radius. Consume a matched prior observation once. Unmatched detections receive
   new IDs. This includes association from the second frame onward.

6. **Filter candidate tracks.** Retain an RSO-candidate track only if it has at
   least `min_track_length` observations and its first-to-last center displacement
   is strictly greater than `min_displacement`. Short tracks are reported as
   rejected candidates. Tracks with enough observations but insufficient net
   displacement are classified as star-like. These categories describe algorithm
   decisions, not independently verified physical identities.

For centers `p` and `q`, all proximity and displacement tests use
`sqrt((p.x - q.x)^2 + (p.y - q.y)^2)` in pixels.

## Default parameters

These defaults preserve the main numerical thresholds in the uploaded detector;
the handling of ordering, frame boundaries, and association has been corrected.

| `DetectorConfig` field | Default | Exact interpretation |
|---|---:|---|
| `threshold` | 1 | Foreground intensity is strictly greater than this value after normalization. |
| `median_window` | 30 | Maximum number of frames in a background segment. |
| `min_area` | 0 | Inclusive lower bound on contour area, in pixels². |
| `max_area` | 50 | Exclusive upper bound on contour area, in pixels². |
| `star_radius` | 6 | A persistent source is nearby when center distance is `< 6` pixels. |
| `match_radius` | 20 | Candidate association requires distance `< 20` pixels. |
| `star_match_radius` | 5 | Star-like association requires distance `< 5` pixels. |
| `min_displacement` | 8 | Retained candidate tracks must move `> 8` pixels from first to last observation. |
| `min_track_length` | 2 | Minimum observation count for a retained candidate track. |

OpenCV contour area is not the number of foreground pixels or bounding-box area.
An isolated pixel can have contour area zero and is accepted by the default area
filter. With an even number of binary frames, the median can be 127 after casting
to `uint8`; contour extraction treats that nonzero value as foreground. A source
present in exactly half the frames can therefore enter the background model.

## Interpretation and limitations

- **Persistent backgrounds:** The method assumes stars remain sufficiently close
  to their segment background positions. Substantial drift, jitter, or camera
  motion can create moving-object candidates. There is no registration or
  astrometric correction in this package.
- **Frame cadence:** Matching radii are measured in pixels per adjacent frame;
  the detector does not use timestamps. A change in image scale, cadence, or
  missed frames can require different settings.
- **Association:** There is no velocity or direction model, trajectory prediction,
  global assignment, or gap re-identification. Crossings and dense detections can
  lead to ID swaps; a missed frame ends continuity.
- **Motion filtering:** The displacement test measures the straight-line distance
  between a track's endpoints. A curved trajectory returning near its start can
  fail despite substantial travel. A faint or brief transit may fail the length
  or displacement requirements.
- **Background contamination:** Slowly moving targets can enter the median model.
  Targets near persistent-source centers can be rejected by the proximity filter.
  Very short median segments provide weak separation of static and moving
  sources; a one-frame segment contains that frame's entire foreground.
- **Intensity and morphology:** Per-frame normalization and a threshold of 1 are
  inherited defaults, not an adaptive noise model. They may be unsuitable for
  unprocessed noisy images. Large streaks or merged contours can exceed the area
  cutoff. No photometric calibration or brightness estimation is performed.

Returned bounding-box and contour-area metadata support inspection. They were
added during packaging and should not be confused with a new detection method or
a reproduced paper benchmark. Review detections against independent annotations
before drawing scientific performance conclusions.
