import tempfile
import unittest
from itertools import product
from pathlib import Path

import numpy as np

from data_processing.trips import load_reference, load_trip
from evaluation.metrics import consecutive_unique, route_metrics, sequence_f1, top_one
from evaluation.reciprocal_experiments import ReciprocalPenaltyRouter
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

    def test_sequence_f1_against_scalar_lcs(self):
        sequences = [p for n in range(5) for p in product(range(2), repeat=n)]
        for left, right in product(sequences, repeat=2):
            dp = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
            for i, a in enumerate(left, 1):
                for j, b in enumerate(right, 1):
                    dp[i][j] = dp[i - 1][j - 1] + 1 if a == b else max(dp[i - 1][j], dp[i][j - 1])
            self.assertEqual(sequence_f1(left, right), 2 * dp[-1][-1] / max(len(left) + len(right), 1))
        self.assertEqual(consecutive_unique([4, 4, -1, 4, 2, 4]), [4, 2, 4])

    def test_diagnostics_distinguish_gap_and_invalid_time(self):
        self.write("track", "8.0005 49 1\n8.0006 49 1\n8.0007 49 40\n")
        trip = load_trip(self.path)
        sample = candidates(trip)
        probabilities = np.where(sample.ids == 0, .99, .001)
        diagnostics = {}
        result = viterbi(trip, sample, probabilities, diagnostics=diagnostics)
        self.assertEqual(result.legs, [[0], [0], [0]])
        self.assertEqual(diagnostics["gap_resets"], 1)
        self.assertEqual(diagnostics["invalid_time_resets"], 1)
        self.assertEqual(diagnostics["selected_transition_restarts"], 0)

    def test_bridge_arc_order_and_candidate_miss(self):
        self.write("nodes", "8 49\n8.001 49\n8.002 49\n8.003 49\n8.004 49\n")
        self.write("arcs", "0 1\n2 3\n3 4\n1 2\n1 0\n0 2\n")
        trip = load_trip(self.path)
        router = RoadRouter(trip, 450.)
        self.assertEqual(router.bridge(0, 2), [3, 1])
        self.assertIsNone(router.bridge(2, 0))
        row = route_metrics(np.array([0, 2]), np.array([[0], [2]]), np.array([0, 1]),
                            trip.arcs, [0, 3, 1, 2], [0, 3, 1, 2])
        self.assertEqual(row["candidate_miss"], .5)
        self.assertEqual(row["top1"], .5)
        self.assertEqual(row["continuity"], 0)
        self.assertEqual(row["sequence_f1"], 1)

    def test_reciprocal_penalty_is_soft_and_directional(self):
        trip = load_trip(self.path)
        config = DecoderConfig()
        router = ReciprocalPenaltyRouter(trip, config.max_network_distance)
        args = (np.array([0]), np.array([1, 3]), np.array([.9]), np.array([.1, .1]),
                14.6, 1., config)
        original = router.transitions(*args)
        router.penalty = 3.
        adjusted = router.transitions(*args)
        self.assertTrue(np.isfinite(adjusted).all())
        np.testing.assert_allclose(original - adjusted, [[0., 3.]])


if __name__ == "__main__":
    unittest.main()
