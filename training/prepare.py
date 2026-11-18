"""Build a reproducible candidate dataset from the two authorized development splits."""
import argparse
from pathlib import Path

import numpy as np

from data_processing.trips import DEVELOPMENT, load_reference, load_trip, trips
from evaluation.reference import align_reference
from features.candidates import candidates


def prepare(root, output):
    output.mkdir(parents=True, exist_ok=True)
    seen = set()
    for partition, expected in zip(DEVELOPMENT, (80, 10)):
        directories = trips(root, partition)
        if len(directories) != expected:
            raise ValueError(f"Expected {expected} trips in {partition}, found {len(directories)}")
        for directory in directories:
            if directory.name in seen:
                raise ValueError(f"Duplicate development trip ID: {directory.name}")
            seen.add(directory.name)
            trip = load_trip(directory)
            route = load_reference(directory, trip)
            labels, residual = align_reference(trip, route)
            sample = candidates(trip)
            if not (labels >= 0).any():
                raise ValueError(f"No usable alignment in {directory.name}")
            np.savez_compressed(output / f"{partition}-{directory.name}.npz",
                                features=sample.features, labels=labels, ids=sample.ids,
                                residual=residual, fractions=sample.fractions,
                                arcs=trip.arcs, route=route)
            print(partition, directory.name, int((labels >= 0).sum()), len(labels), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/candidates"))
    args = parser.parse_args()
    prepare(args.data, args.cache)
