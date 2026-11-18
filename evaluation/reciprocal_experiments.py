"""Test reciprocal-edge transition penalties after the training baseline audit."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from data_processing.trips import load_reference, load_trip, trips
from evaluation.metrics import score_candidates
from evaluation.reference import align_reference
from evaluation.sequence_experiments import OUTPUT, digest, score, summarize, write
from features.candidates import candidates
from route_reconstruction.decoder import DecoderConfig, RoadRouter, viterbi


class ReciprocalPenaltyRouter(RoadRouter):
    def __init__(self, trip, limit):
        super().__init__(trip, limit)
        self.penalty = 0.

    def transitions(self, left, right, x, y, observed, elapsed, config):
        matrix = super().transitions(left, right, x, y, observed, elapsed, config)
        a, b = self.trip.arcs[left], self.trip.arcs[right]
        reciprocal = ((a[:, None, 0] == b[None, :, 1]) &
                      (a[:, None, 1] == b[None, :, 0]) &
                      (a[:, None, 0] != a[:, None, 1]))
        return matrix - self.penalty * reciprocal


def reciprocal_hops(trip, legs):
    return sum(int((edges[:-1] == edges[1:, ::-1]).all(axis=1).sum())
               for leg in legs if len(leg) > 1 for edges in [trip.arcs[leg]])


def run(data, output):
    protocol = json.loads((output / "protocol.json").read_text())
    baseline = json.loads((output / "baseline.json").read_text())
    base_rows = {r["trip"]: r for r in baseline["trips"]}
    directories = {p.name: p for p in trips(data, "train")}
    if len(directories) != 80 or set(directories) != set(base_rows):
        raise ValueError("Development paths must match the recorded training-only baseline")
    if any(digest(Path(p)) != sha for p, sha in protocol["hashes"].items()):
        raise ValueError("Frozen baseline inputs changed")
    base = DecoderConfig(**protocol["decoder"])
    penalties = {"reciprocal_3": 3., "reciprocal_8": 8.}
    results, baseline_hops = {name: [] for name in penalties}, {}
    for index, fold in enumerate(protocol["folds"]):
        model = joblib.load(output / f"fold-{index}.joblib")
        for key in fold["validation"]:
            trip = load_trip(directories[key])
            start = perf_counter()
            sample = candidates(trip)
            values = score_candidates(model, sample)
            inference = perf_counter() - start
            plain = viterbi(trip, sample, values, base)
            baseline_hops[key] = reciprocal_hops(trip, plain.legs)
            pending = {}
            for name, penalty in penalties.items():
                start = perf_counter()
                router = ReciprocalPenaltyRouter(trip, base.max_network_distance)
                router.penalty = penalty
                decoded = viterbi(trip, sample, values, base, router)
                pending[name] = decoded, inference + perf_counter() - start
            reference = load_reference(directories[key], trip)
            labels, _ = align_reference(trip, reference)
            assert score(trip, sample, values, plain, reference, labels, {})["sequence_f1"] == base_rows[key]["sequence_f1"]
            for name, (decoded, elapsed) in pending.items():
                row = score(trip, sample, values, decoded, reference, labels, {})
                results[name].append(row | dict(trip=key, fold=index, seconds=elapsed,
                                                reciprocal_hops=reciprocal_hops(trip, decoded.legs)))
        print("Reciprocal trials fold", index, flush=True)
    comparisons = {}
    for name, records in results.items():
        deltas = [r["sequence_f1"] - base_rows[r["trip"]]["sequence_f1"] for r in records]
        comparisons[name] = dict(penalty=penalties[name], summary=summarize(records),
            improved=sum(d > 1e-12 for d in deltas), worse=sum(d < -1e-12 for d in deltas),
            fold_deltas=[float(np.mean([d for r, d in zip(records, deltas) if r["fold"] == i]))
                         for i in range(3)], trips=records)
    write(output / "reciprocal.json", dict(baseline_hops=baseline_hops, trials=comparisons))
    for name, trial in comparisons.items():
        print(name, trial["summary"], trial["fold_deltas"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.data, args.output)
