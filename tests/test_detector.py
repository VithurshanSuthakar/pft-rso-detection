"""Regression tests using synthetic arrays only; no research images are needed."""

from __future__ import annotations

import unittest

import numpy as np

from pft_rso import DetectorConfig, detect_sequence, preprocess_frame


def frame(*points: tuple[int, int]) -> np.ndarray:
    """Make a small binary image from (x, y) point coordinates."""
    image = np.zeros((64, 128), dtype=np.uint8)
    for x, y in points:
        image[y, x] = 255
    return image


def observations(result):
    return result.rsos + result.stars + result.rejected


class DetectorRegressionTests(unittest.TestCase):
    def test_moving_candidate_and_static_source_with_first_frame_continuity(self):
        images = [frame((10 + 3 * i, 10), (90, 45)) for i in range(12)]
        before = [image.copy() for image in images]
        result = detect_sequence(images)

        self.assertEqual(result.frame_count, 12)
        self.assertEqual(result.image_shape, (64, 128))
        self.assertEqual([item.frame for item in result.rsos], list(range(12)))
        self.assertEqual([item.x for item in result.rsos], [10 + 3 * i for i in range(12)])
        self.assertEqual(len({item.object_id for item in result.rsos}), 1)
        self.assertEqual(len({item.object_id for item in result.stars}), 1)
        self.assertEqual({(item.x, item.y) for item in result.stars}, {(90, 45)})
        self.assertTrue({item.object_id for item in result.rsos}.isdisjoint(
            item.object_id for item in result.stars
        ))
        self.assertFalse(result.rejected)
        for original, current in zip(before, images):
            np.testing.assert_array_equal(current, original)

    def test_terminal_median_blocks_process_all_input_indices(self):
        # Lengths 1, 31 and 61 formerly produced an empty final median block.
        for count in (1, 30, 31, 60, 61):
            with self.subTest(frame_count=count):
                result = detect_sequence([frame((20, 20)) for _ in range(count)])
                self.assertEqual(result.frame_count, count)
                self.assertEqual([item.frame for item in result.stars], list(range(count)))
                self.assertFalse(result.rsos)
                self.assertFalse(result.rejected)

    def test_first_frame_of_new_block_uses_its_own_median(self):
        images = [frame((12, 20)) for _ in range(30)]
        images += [frame((45, 20)) for _ in range(30)]
        result = detect_sequence(images)
        self.assertEqual([item.frame for item in result.stars], list(range(60)))
        self.assertEqual(next(item.x for item in result.stars if item.frame == 30), 45)
        self.assertFalse(result.rsos)
        self.assertFalse(result.rejected)

    def test_final_image_contributes_to_even_length_median(self):
        # Presence in exactly half a block gives median 127, still foreground.
        # Excluding the last image would turn this into a rejected short track.
        images = [frame(), frame(), frame((30, 20)), frame((30, 20))]
        result = detect_sequence(images, DetectorConfig(min_track_length=3))
        self.assertEqual([item.frame for item in result.stars], [2, 3])
        self.assertFalse(result.rejected)

    def test_previous_observation_is_consumed_once_in_both_classes(self):
        for use_median_star in (True, False):
            with self.subTest(background_class=use_median_star):
                tail = frame((50, 30)) if use_median_star else frame()
                images = [frame((50, 30)), frame((48, 30), (52, 30))]
                images += [tail.copy() for _ in range(3)]
                result = detect_sequence(images)
                second = [item for item in observations(result) if item.frame == 1]
                self.assertEqual(len(second), 2)
                self.assertEqual(len({item.object_id for item in second}), 2)
                first_id = next(item.object_id for item in observations(result) if item.frame == 0)
                self.assertEqual(sum(item.object_id == first_id for item in second), 1)

    def test_missing_frame_starts_a_new_track(self):
        positions = [10, 13, None, 19, 22, 25, 28]
        images = [frame() if x is None else frame((x, 10)) for x in positions]
        result = detect_sequence(images)
        by_frame = {item.frame: item for item in observations(result)}
        self.assertNotIn(2, by_frame)
        self.assertEqual(by_frame[0].object_id, by_frame[1].object_id)
        self.assertNotEqual(by_frame[1].object_id, by_frame[3].object_id)
        self.assertEqual({item.frame for item in result.rsos}, {3, 4, 5, 6})

    def test_geometric_contour_area_includes_zero_and_excludes_fifty(self):
        image = frame((5, 5))
        image[10:18, 10:18] = 255  # 8 x 8 pixels, contour area 7 * 7 = 49.
        image[30:36, 30:41] = 255  # 11 x 6 pixels, contour area 10 * 5 = 50.
        result = detect_sequence([image])
        self.assertEqual(sorted(item.contour_area for item in observations(result)), [0.0, 49.0])
        square = next(item for item in result.stars if item.contour_area == 49)
        self.assertEqual((square.x, square.y), (14, 14))
        self.assertEqual((square.bbox_x, square.bbox_y, square.width, square.height), (10, 10, 8, 8))

    def test_star_proximity_is_strictly_less_than_six(self):
        images = [frame((50, 20), (55, 20)), frame((50, 20), (56, 20))]
        images += [frame((50, 20)) for _ in range(3)]
        result = detect_sequence(images)
        self.assertIn((0, 55), {(item.frame, item.x) for item in result.stars})
        self.assertIn((1, 56), {(item.frame, item.x) for item in result.rejected})

    def test_association_radii_have_strict_boundaries(self):
        result = detect_sequence([frame((x, 20)) for x in (10, 30, 49)])
        by_frame = {item.frame: item for item in observations(result)}
        self.assertNotEqual(by_frame[0].object_id, by_frame[1].object_id)
        self.assertEqual(by_frame[1].object_id, by_frame[2].object_id)
        self.assertEqual([item.frame for item in result.rejected], [0])

        # All five observations are near the median star, but a 5-pixel step
        # is outside the strictly-less-than-5 background association gate.
        images = [frame((x, 20)) for x in (10, 15, 15, 15, 15)]
        result = detect_sequence(images, DetectorConfig(star_radius=10))
        self.assertEqual(len(result.stars), 5)
        self.assertNotEqual(result.stars[0].object_id, result.stars[1].object_id)
        self.assertEqual(len({item.object_id for item in result.stars[1:]}), 1)

    def test_endpoint_displacement_must_exceed_eight(self):
        for last_x, retained in ((18, False), (19, True)):
            with self.subTest(endpoint=last_x):
                result = detect_sequence([frame((x, 20)) for x in (10, 14, last_x)])
                self.assertEqual(len(result.rsos), 3 if retained else 0)
                self.assertEqual(len(result.stars), 0 if retained else 3)
                self.assertFalse(result.rejected)

    def test_native_uint16_normalization_constants_and_threshold(self):
        image = np.array([[1000, 1001, 1002]], dtype=np.uint16)
        original = image.copy()
        actual = preprocess_frame(image)
        np.testing.assert_array_equal(actual, np.array([[0, 255, 255]], dtype=np.uint8))
        np.testing.assert_array_equal(image, original)
        self.assertEqual(actual.dtype, np.uint8)
        self.assertFalse(preprocess_frame(np.full((3, 4), 40000, dtype=np.uint16)).any())
        np.testing.assert_array_equal(
            preprocess_frame(np.array([[0, 1, 2, 255]], dtype=np.uint8)),
            np.array([[0, 0, 255, 255]], dtype=np.uint8),
        )

    def test_invalid_configuration_fails_before_detection(self):
        invalid = [
            {"median_window": 0}, {"median_window": True},
            {"threshold": 256}, {"threshold": -1},
            {"min_track_length": 1}, {"max_area": 0},
            {"min_area": 50, "max_area": 50},
            {"star_radius": float("nan")}, {"match_radius": float("inf")},
            {"star_match_radius": 0}, {"min_displacement": -1},
        ]
        for kwargs in invalid:
            with self.subTest(config=kwargs), self.assertRaises(ValueError):
                DetectorConfig(**kwargs)

    def test_invalid_sequence_and_preprocessing_inputs_fail_clearly(self):
        invalid_sequences = [
            [], [np.zeros((0, 3), dtype=np.uint8)],
            [np.zeros((3, 3, 3), dtype=np.uint8)],
            [np.zeros((3, 3), dtype=np.float32)],
            [np.full((3, 3), 1, dtype=np.uint8)],
            [frame(), np.zeros((5, 5), dtype=np.uint8)],
        ]
        for index, images in enumerate(invalid_sequences):
            with self.subTest(case=index), self.assertRaises(ValueError):
                detect_sequence(images)
        with self.assertRaises(TypeError):
            detect_sequence(["not an image"])
        with self.assertRaises(TypeError):
            detect_sequence([frame()], config={})
        for image in (np.zeros((2, 2), dtype=np.float64), np.zeros((2, 2, 2), dtype=np.uint8)):
            with self.subTest(shape=image.shape, dtype=image.dtype), self.assertRaises(ValueError):
                preprocess_frame(image)


if __name__ == "__main__":
    unittest.main()
