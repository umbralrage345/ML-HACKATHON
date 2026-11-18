"""Inference service. Reference data is never loaded here."""
from dataclasses import dataclass

from data_processing.trips import Trip, load_trip
from evaluation.metrics import score_candidates
from features.candidates import Candidates, candidates
from route_reconstruction.decoder import Decoded, DecoderConfig, viterbi


@dataclass
class Prediction:
    trip: Trip
    sample: Candidates
    decoded: Decoded


def predict(directory, bundle):
    trip = load_trip(directory)
    sample = candidates(trip)
    scores = score_candidates(bundle["model"], sample)
    return Prediction(trip, sample, viterbi(trip, sample, scores, DecoderConfig(**bundle["decoder"])))
