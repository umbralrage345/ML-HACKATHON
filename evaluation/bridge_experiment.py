"""Evaluate reciprocal penalties on the actual traversed bridge boundaries."""
import argparse
from functools import lru_cache
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from data_processing.trips import load_reference, load_trip, trips
from evaluation.metrics import score_candidates
from evaluation.reference import align_reference
from evaluation.reciprocal_experiments import ReciprocalPenaltyRouter, reciprocal_hops
from evaluation.sequence_experiments import OUTPUT, digest, score, summarize, write
from features.candidates import candidates
from route_reconstruction.decoder import DecoderConfig, viterbi


class BridgeAwareRouter(ReciprocalPenaltyRouter):
    """Apply one soft penalty per reversal, including at shortest-path seams."""

    def __init__(self, trip, limit):
        super().__init__(trip, limit)
        self.boundaries = lru_cache(maxsize=32768)(self._boundaries)

    def _boundaries(self, source, target):
        _, parents = self.paths(source)
        last = parents[target][0]
        first = target
        while parents[first][0] != source:
            first = parents[first][0]
        return first, last

    def transitions(self, left, right, x, y, observed, elapsed, config):
        matrix = super().transitions(left, right, x, y, observed, elapsed, config)
        a, b = self.trip.arcs[left], self.trip.arcs[right]
        # Same-arc stays and adjacent arcs have no intermediate bridge.
        bridges = (np.isfinite(matrix) & (left[:, None] != right[None, :]) &
                   (a[:, None, 1] != b[None, :, 0]))
        for i, j in zip(*np.nonzero(bridges)):
            first, last = self.boundaries(a[i, 1], b[j, 0])
            count = int(first == a[i, 0]) + int(last == b[j, 1])
            matrix[i, j] -= self.penalty * count
        return matrix


def run(data, previous, output):
    def read(name):
        return json.loads((previous / f"{name}.json").read_text())

    protocol = read("protocol")
    reference_results = {row["trip"]: row for row in read("reciprocal")["trials"]["reciprocal_3"]["trips"]}
    model_hashes = read("fold_artifacts")
    directories = {entry.name: entry for entry in trips(data, "train")}
    if len(directories) != 80 or directories.keys() != reference_results.keys():
        raise ValueError("Training trip IDs must match the recorded benchmark")
    if any(digest(Path(p)) != h for p, h in protocol["hashes"].items()):
        raise ValueError("Frozen artifact or historical result changed")
    if any(digest(previous / p) != h for p, h in model_hashes.items()):
        raise ValueError("Grouped fold artifact changed")
    config = DecoderConfig(**protocol["decoder"])
    output.mkdir(parents=True, exist_ok=False)
    records = {"benchmark": [], "candidate": []}
    for fold, split in enumerate(protocol["folds"]):
        assert set(split["fit"]).isdisjoint(split["validation"])
        model = joblib.load(previous / f"fold-{fold}.joblib")
        for key in split["validation"]:
            trip = load_trip(directories[key])
            start = perf_counter()
            sample = candidates(trip)
            probabilities = score_candidates(model, sample)
            shared = perf_counter() - start
            decoded_by_variant = {}
            types = [("benchmark", ReciprocalPenaltyRouter), ("candidate", BridgeAwareRouter)]
            if len(records["benchmark"]) % 2:
                types.reverse()
            for name, router_type in types:
                start = perf_counter()
                router = router_type(trip, config.max_network_distance)
                router.penalty = 3.
                decoded = viterbi(trip, sample, probabilities, config, router)
                decoded_by_variant[name] = decoded, shared + (perf_counter() - start)

            reference = load_reference(directories[key], trip)
            labels, _ = align_reference(trip, reference)
            for name, (decoded, seconds) in decoded_by_variant.items():
                row = score(trip, sample, probabilities, decoded, reference, labels, {})
                row.update(trip=key, fold=fold, seconds=seconds,
                           reciprocal_hops=reciprocal_hops(trip, decoded.legs))
                if name == "benchmark":
                    assert all(v == row[k] for k, v in reference_results[key].items()
                               if k != "seconds"), key
                records[name].append(row)
        print("Completed fold", fold, flush=True)

    before, after = records["benchmark"], records["candidate"]
    assert len(before) == len(after) == 80
    deltas = [b["sequence_f1"] - a["sequence_f1"] for a, b in zip(before, after, strict=True)]
    result = dict(protocol=protocol, fold_artifact_hashes=model_hashes, penalty=3,
                  summaries={name: summarize(rows) for name, rows in records.items()},
                  folds=[{name: summarize([row for row in rows if row["fold"] == i])
                          for name, rows in records.items()} for i in range(3)],
                  improved=sum(d > 1e-12 for d in deltas), declined=sum(d < -1e-12 for d in deltas),
                  tied=sum(abs(d) <= 1e-12 for d in deltas), trips=records)
    write(output / "results.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("protocol", "trips")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--previous", type=Path, default=OUTPUT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.data, args.previous, args.output)
