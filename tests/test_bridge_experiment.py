"""Synthetic checks for the bridge-aware experimental score."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from data_processing.trips import load_trip
from evaluation.bridge_experiment import BridgeAwareRouter
from evaluation.reciprocal_experiments import ReciprocalPenaltyRouter
from features.candidates import Candidates
from route_reconstruction.decoder import DecoderConfig, viterbi


class BridgePenaltyTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name) / "synthetic"
        directory.mkdir()
        for suffix, rows in {
            "nodes": "8 49\n8.0002 49\n8.0004 49\n8.0006 49\n",
            "track": "8.00018 49 1\n8.00016 49 2\n",
            "arcs": "0 1\n1 0\n0 2\n2 1\n1 3\n0 1\n",
        }.items():
            (directory / f"synthetic.{suffix}").write_text(rows)
        self.trip = load_trip(directory)
        self.config = DecoderConfig()
        self.base = ReciprocalPenaltyRouter(self.trip, 450.)
        self.candidate = BridgeAwareRouter(self.trip, 450.)
        self.base.penalty = self.candidate.penalty = 3.

    def transition(self, router, left, right):
        return router.transitions(np.array([left]), np.array([right]), np.array([.9]),
                                  np.array([.1]), 15., 1., self.config)[0, 0]

    def test_first_last_and_both_bridge_boundaries(self):
        for left, right, extra_penalty in [(0, 2, 3), (3, 0, 3), (0, 5, 6), (0, 4, 0), (0, 1, 0)]:
            self.assertAlmostEqual(self.transition(self.base, left, right)
                                   - self.transition(self.candidate, left, right), extra_penalty)
        self.assertEqual(self.candidate.bridge(0, 2), [1])

    def test_supported_uturn_stays_in_one_leg(self):
        sample = Candidates(np.array([[0], [1]]), np.array([[.9], [.2]]), np.zeros((2, 1, 1)))
        result = viterbi(self.trip, sample, np.ones((2, 1)), self.config, self.candidate)
        self.assertEqual(result.legs, [[0, 1]])

    def test_connected_repeat_keeps_its_intermediate_arc(self):
        sample = Candidates(np.array([[0], [5]]), np.array([[.9], [.1]]), np.zeros((2, 1, 1)))
        result = viterbi(self.trip, sample, np.ones((2, 1)), self.config, self.candidate)
        self.assertEqual(result.legs, [[0, 1, 5]])
