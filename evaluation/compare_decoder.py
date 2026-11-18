"""Select decoder parameters on student trips and generate real prediction maps."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np

from data_processing.trips import load_trip, trips
from evaluation.metrics import route_metrics, score_candidates, top_one
from features.candidates import Candidates
from route_reconstruction.decoder import DecoderConfig, RoadRouter, viterbi
from training.experiment import save_json
from visualizations.maps import make_map


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    selection = json.loads((args.output / "selection.json").read_text())
    model = joblib.load(args.artifacts / f"{selection['deployed']}.joblib")
    settings = [DecoderConfig(beta=b, gps_sigma=s, break_penalty=p)
                for b, s, p in [(15., 35., 10.), (30., 35., 10.), (55., 60., 12.)]]
    baseline, choices = {}, [dict(config=asdict(config), trips={}) for config in settings]
    for directory in trips(args.data, "student_test"):
        trip = load_trip(directory)
        with np.load(args.artifacts / "candidates" / f"student_test-{directory.name}.npz") as cache:
            sample = Candidates(cache["ids"], cache["fractions"], cache["features"])
            labels, route = cache["labels"], cache["route"]
        probs = score_candidates(model, sample)
        baseline[directory.name] = route_metrics(top_one(sample.ids, probs), sample.ids, labels,
                                                 trip.arcs, route)
        router = RoadRouter(trip, settings[0].max_network_distance)
        for config, choice in zip(settings, choices):
            start = perf_counter()
            decoded = viterbi(trip, sample, probs, config, router)
            stats = route_metrics(decoded.points, sample.ids, labels, trip.arcs, route, decoded.route)
            choice["trips"][directory.name] = stats | dict(decode_seconds=perf_counter() - start,
                                                            route_legs=len(decoded.legs))
        print("decoded", directory.name, flush=True)

    def summarize(rows):
        keys = ("top1", "continuity", "sequence_f1")
        return {key: float(np.mean([row[key] for row in rows.values() if row[key] is not None]))
                for key in keys}

    for choice in choices:
        choice["mean_by_trip"] = summarize(choice["trips"])
    winner = max(choices, key=lambda choice: (choice["mean_by_trip"]["sequence_f1"],
                                              choice["mean_by_trip"]["top1"]))
    config = DecoderConfig(**winner["config"])
    save_json(args.output / "decoder.json", dict(classifier=dict(trips=baseline, mean_by_trip=summarize(baseline)),
              decoder_trials=choices, selected=winner["config"]))
    joblib.dump(dict(model=model, decoder=asdict(config)), args.artifacts / "pathsnap.joblib", compress=3)
    directory = trips(args.data, "student_test")[0]
    trip = load_trip(directory)
    with np.load(args.artifacts / "candidates" / f"student_test-{directory.name}.npz") as cache:
        sample = Candidates(cache["ids"], cache["fractions"], cache["features"])
        decoded = viterbi(trip, sample, score_candidates(model, sample), config)
        make_map(trip, nearby=np.unique(sample.ids[:, :3]), reference=cache["route"],
                 predicted=decoded.route).save(str(args.output / "student_prediction_map.html"))


if __name__ == "__main__":
    main()
