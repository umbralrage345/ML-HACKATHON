import tempfile
import unittest
from pathlib import Path

import numpy as np

from data_processing.trips import load_reference, load_trip
from evaluation.metrics import sequence_f1, top_one
from evaluation.reference import align_reference
from features.candidates import candidates
from route_reconstruction.decoder import DecoderConfig, RoadRouter, viterbi


class SyntheticRoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "trip"
        self.path.mkdir()
        self.write("nodes", "8 49\n8.001 49\n8.002 49\n8.003 49\nbad\n")
        self.write("arcs", "0 1\n1 2\n2 3\n1 0\n4 0\n")
        self.write("track", "8.0005 49 1\n8.0025 49 5\nbad\n8.0027 49 100\n")

    def write(self, extension, text):
        (self.path / f"trip.{extension}").write_text(text, encoding="ascii")

    def test_raw_indices_and_optional_reference(self):
        trip = load_trip(self.path)
        self.assertEqual(trip.good.tolist(), [True, True, False, True])
        self.assertEqual(trip.valid.tolist(), [True, True, True, True, False])
        self.assertAlmostEqual(trip.length[0], 73, delta=1)
        with self.assertRaises(FileNotFoundError):
            load_reference(self.path, trip)
        self.write("route", "4\n")
        with self.assertRaises(ValueError):
            load_reference(self.path, trip)

    def test_alignment_preserves_order_with_unobserved_arc(self):
        self.write("route", "0\n1\n2\n")
        trip = load_trip(self.path)
        labels, residual = align_reference(trip, load_reference(self.path, trip))
        self.assertEqual(labels.tolist(), [0, 2, -1, 2])
        self.assertLess(max(residual[trip.good]), 1e-7)

    def test_directed_reconstruction_preserves_rows_and_fills_bridge(self):
        trip = load_trip(self.path)
        sample = candidates(trip)
        scores = np.where(sample.ids == np.array([0, 2, -1, 2])[:, None], .99, .001)
        self.assertEqual(top_one(sample.ids, scores).tolist(), [0, 2, -1, 2])
        router = RoadRouter(trip, 450.)
        self.assertEqual(router.bridge(0, 2), [1])
        self.assertIsNone(router.bridge(2, 0))
        result = viterbi(trip, sample, scores, DecoderConfig(), router)
        self.assertEqual(result.points.tolist(), [0, 2, -1, 2])
        self.assertEqual(result.legs, [[0, 1, 2], [2]])

    def test_sequence_metric_preserves_order_and_repeats(self):
        self.assertEqual(sequence_f1([3, 1, 3], [3, 3, 1]), 2 / 3)
        self.assertEqual(sequence_f1([3, 1, 3], [3, 1, 3]), 1)


if __name__ == "__main__":
    unittest.main()
