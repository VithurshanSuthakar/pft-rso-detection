# Validation record

Preparation date: **17 November 2026**. Package version: **0.1.0**.

## Local environment

The package was built into a wheel and installed into a clean Python environment
with its declared dependencies. Verification used Linux, Python **3.12.14**,
NumPy **2.5.5**, and `opencv-python-headless` **4.14.0.94** (OpenCV reports
**4.14.0** at runtime). `pft-detect --version` returned `0.1.0`.

The package declares Python 3.10 or later. The included GitHub Actions workflow
is configured for Python 3.10 and 3.12. That configuration is not a claim that
remote CI or other operating systems have already been tested.

## Functional checks

**21 unittest tests passed** against the installed package. Test inputs were
generated in memory or in temporary directories. Checks cover:

- Separation of a moving point source from a stationary source.
- Processing and association from frame zero through the second frame.
- Final median blocks for sequence lengths 1, 30, 31, 60, and 61.
- Correct median-reference changes at block boundaries.
- The final image's contribution and half-occupancy foreground behavior.
- One-to-one previous-observation assignment for both categories.
- New IDs after missed frames.
- Strict area, proximity, association, intensity, and displacement boundaries.
- Native 16-bit preprocessing, constant inputs, invalid parameters and images.
- Natural filename ordering and explicit alignment of coordinates and filenames.
- CSV headers, frame-zero records, and preservation of nonempty output directories.
- JSON settings with CLI overrides, malformed input, and TIFF stack rejection.
- Running the installed module from outside the source directory.
- Overlay generation only when requested and preservation of source image bytes.

Run the checks with:

```bash
python -m pip install .
python -m unittest discover -s tests -v
```

## Documented example

The included generator and installed CLI were run end to end on **48 synthetic
128 x 128 uint16 frames**, using the default parameters and `--save-overlays`.

| Output | Observed value |
| --- | ---: |
| Processed frames | 48 |
| Retained moving-candidate observations | 48 |
| Retained candidate IDs | 1 |
| Star-like observations | 144 |
| Short-track observations | 1 |
| Local overlay files | 48 |

The synthetic sequence contains three stationary sources, one translating source,
and one single-frame artifact. These numbers confirm the expected behavior of the
toy example; they are not precision, recall, or an evaluation on real imagery.

## Source and data handling

The reference scripts were checked byte-for-byte against the uploaded archive;
their SHA-256 values are recorded in [legacy/README.md](../legacy/README.md).
Input images, original CSVs, videos, IDE files, and the paper PDF are excluded from
the repository. The repository audit checks the Git index for source-only content,
and the downloadable source archive is built from that checked index.

No observational input images were used for the validation described here. The
publication's dataset scores have not been reproduced. See
[paper and provenance](paper-and-provenance.md) for the limits of the connection
between the supplied scripts and the publication.

