"""IO and CLI integration checks using temporary, generated images only."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import csv
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cv2
import numpy as np

from pft_rso import detect_sequence
from pft_rso.cli import main
from pft_rso.io import LEGACY_COLUMNS, discover_images, load_sequence, write_results


class IOAndCLIIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @staticmethod
    def _write_image(path: Path, image: np.ndarray) -> None:
        success, encoded = cv2.imencode(path.suffix.lower(), image)
        if not success:
            raise RuntimeError(f"Could not encode synthetic test image {path.name}")
        encoded.tofile(path)

    def _sequence(self, directory: Path) -> Path:
        directory.mkdir()
        # Creation order intentionally differs from temporal filename order.
        for name, x in (("frame10.tif", 30), ("frame1.tif", 10), ("frame2.tif", 20)):
            image = np.full((64, 64), 1000, dtype=np.uint16)
            image[8:11, 50:53] = 60000
            image[40:43, x:x + 3] = 40000
            self._write_image(directory / name, image)
        return directory

    def _run_main(self, arguments: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_natural_sorting_ignores_unrelated_and_nested_files(self) -> None:
        inputs = self._sequence(self.root / "input")
        (inputs / "notes.txt").write_text("Not an image", encoding="utf-8")
        nested = inputs / "nested"
        nested.mkdir()
        self._write_image(nested / "frame0.png", np.zeros((4, 4), dtype=np.uint8))
        self.assertEqual(
            [path.name for path in discover_images(inputs)],
            ["frame1.tif", "frame2.tif", "frame10.tif"],
        )

    def test_exports_align_frame_zero_coordinates_and_filenames(self) -> None:
        inputs = self._sequence(self.root / "input")
        paths, frames = load_sequence(inputs)
        result = detect_sequence(frames)
        output = write_results(result, paths, self.root / "results")
        with (output / "frame_data.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            self.assertEqual(reader.fieldnames, LEGACY_COLUMNS)
        self.assertEqual([int(row["Frame"]) for row in rows], [0, 1, 2])
        self.assertEqual([int(row["X-Coordinate"]) for row in rows], [11, 21, 31])
        self.assertEqual([int(row["Y-Coordinate"]) for row in rows], [41, 41, 41])
        self.assertEqual(len({row["Object ID"] for row in rows}), 1)
        with (output / "frames.csv").open(newline="", encoding="utf-8") as stream:
            mapping = list(csv.DictReader(stream))
        self.assertEqual(mapping, [
            {"frame": "0", "filename": "frame1.tif"},
            {"frame": "1", "filename": "frame2.tif"},
            {"frame": "2", "filename": "frame10.tif"},
        ])
        with (output / "detections.csv").open(newline="", encoding="utf-8") as stream:
            details = list(csv.DictReader(stream))
        self.assertTrue(details)
        for row in details:
            self.assertEqual(row["filename"], mapping[int(row["frame"])]["filename"])
            self.assertEqual(Path(row["filename"]).name, row["filename"])
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {"frame_data.csv", "star_data.csv", "rejected_data.csv", "frames.csv", "detections.csv", "run.json"},
        )

    def test_nonempty_output_is_preserved(self) -> None:
        inputs = self._sequence(self.root / "input")
        output = self.root / "results"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_bytes(b"existing user content")
        code, _, error = self._run_main(["--input", str(inputs), "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertIn("new or empty", error)
        self.assertEqual(sentinel.read_bytes(), b"existing user content")
        self.assertEqual([path.name for path in output.iterdir()], ["keep.txt"])
        self.assertEqual(len(list(inputs.glob("*.tif"))), 3)

    def test_malformed_and_mismatched_images_are_rejected(self) -> None:
        with self.subTest("malformed image"):
            inputs = self.root / "malformed"
            inputs.mkdir()
            (inputs / "frame1.png").write_bytes(b"not image bytes")
            with self.assertRaisesRegex(ValueError, "Invalid image frame1.png"):
                load_sequence(inputs)
        with self.subTest("mismatched dimensions"):
            inputs = self.root / "mixed"
            inputs.mkdir()
            self._write_image(inputs / "frame1.png", np.zeros((8, 8), dtype=np.uint8))
            self._write_image(inputs / "frame2.png", np.zeros((9, 8), dtype=np.uint8))
            with self.assertRaisesRegex(ValueError, "dimensions differ"):
                load_sequence(inputs)

    def test_cli_flags_override_json_configuration(self) -> None:
        inputs = self._sequence(self.root / "input")
        config = self.root / "parameters.json"
        config.write_text(json.dumps({
            "threshold": 200,
            "median_window": 20,
            "min_displacement": 100,
        }), encoding="utf-8")
        output = self.root / "results"
        code, _, error = self._run_main([
            "--input", str(inputs), "--output", str(output), "--config", str(config),
            "--threshold", "1", "--min-displacement", "8",
        ])
        self.assertEqual(code, 0, error)
        summary = json.loads((output / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["parameters"]["threshold"], 1)
        self.assertEqual(summary["parameters"]["median_window"], 20)
        self.assertEqual(summary["parameters"]["min_displacement"], 8)
        self.assertEqual(summary["counts"]["rso_observations"], 3)

    def test_multipage_tiff_is_rejected(self) -> None:
        inputs = self.root / "multipage"
        inputs.mkdir()
        path = inputs / "frame1.tif"
        pages = [np.zeros((8, 8), dtype=np.uint16), np.ones((8, 8), dtype=np.uint16)]
        self.assertTrue(cv2.imwritemulti(str(path), pages))
        self.assertEqual(cv2.imcount(str(path)), 2)
        with self.assertRaisesRegex(ValueError, "Multipage TIFF is unsupported"):
            load_sequence(inputs)

    def test_module_cli_only_generates_overlays_when_requested(self) -> None:
        inputs = self._sequence(self.root / "input")
        source_bytes = {path.name: path.read_bytes() for path in inputs.iterdir()}
        for save_overlays in (False, True):
            with self.subTest(overlays=save_overlays):
                output = self.root / ("with_overlays" if save_overlays else "without_overlays")
                arguments = [sys.executable, "-m", "pft_rso", "--input", str(inputs), "--output", str(output)]
                if save_overlays:
                    arguments.append("--save-overlays")
                process = subprocess.run(arguments, cwd=self.root, text=True, capture_output=True, check=False)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertIn("Processed 3 frames", process.stdout)
                summary = json.loads((output / "run.json").read_text(encoding="utf-8"))
                self.assertEqual(summary["overlays_requested"], save_overlays)
                self.assertEqual(summary["frame_index_base"], 0)
                self.assertEqual((output / "overlays").exists(), save_overlays)
                if save_overlays:
                    self.assertEqual(len(list((output / "overlays").glob("*.png"))), 3)
        self.assertEqual({path.name: path.read_bytes() for path in inputs.iterdir()}, source_bytes)

    def test_invalid_configuration_fails_before_output_creation(self) -> None:
        inputs = self._sequence(self.root / "input")
        for index, content in enumerate(({"unknown_parameter": 1}, [1, 2], {"match_radius": -1})):
            with self.subTest(config=content):
                config = self.root / f"invalid_{index}.json"
                config.write_text(json.dumps(content), encoding="utf-8")
                output = self.root / f"output_{index}"
                code, _, error = self._run_main([
                    "--input", str(inputs), "--output", str(output), "--config", str(config),
                ])
                self.assertEqual(code, 2)
                self.assertIn("pft-detect:", error)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
