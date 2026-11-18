"""Run the frozen route baseline and controlled trials on grouped training folds."""
import argparse
from dataclasses import asdict, replace
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from data_processing.trips import load_reference, load_trip, trips
from evaluation.metrics import consecutive_unique, route_metrics, score_candidates
from evaluation.reference import align_reference
from features.candidates import candidates
from route_reconstruction.decoder import DecoderConfig, RoadRouter, viterbi
from training.models import SEED, make_model


OUTPUT = Path("artifacts/experiments/sequence_improvements")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False,
                               default=lambda val: val.item()), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(trip, sample, probabilities, decoded, reference, labels, diagnostics):
    predicted, truth = consecutive_unique(decoded.route), consecutive_unique(reference)
    row = route_metrics(decoded.points, sample.ids, labels, trip.arcs, reference, decoded.route)
    valid = (sample.ids >= 0) & (labels[:, None] >= 0)
    target = sample.ids == labels[:, None]
    candidate_f1 = (float(f1_score(target[valid], probabilities[valid] >= .5,
                                  average="macro", labels=[0, 1], zero_division=0))
                    if valid.any() else None)
    lcs = round(row["sequence_f1"] * (len(predicted) + len(truth)) / 2)
    return row | dict(reference_length=len(reference), predicted_length=len(decoded.route),
                      collapsed_reference_length=len(truth), collapsed_predicted_length=len(predicted),
                      lcs=lcs, sequence_omissions=len(truth) - lcs, sequence_insertions=len(predicted) - lcs,
                      observed_distinct_reference_arcs=len(set(truth) & set(decoded.points)),
                      unique_reference_arcs=len(set(truth)),
                      candidate_macro_f1=candidate_f1, route_legs=len(decoded.legs),
                      restarts=max(len(decoded.legs) - 1, 0), unmatched=int((decoded.points < 0).sum()),
                      **diagnostics)


def summarize(rows):
    metrics = ("sequence_f1", "top1", "continuity", "candidate_miss", "candidate_macro_f1", "seconds")
    summary = {key: float(np.mean([r[key] for r in rows if r[key] is not None])) for key in metrics}
    known = [r for r in rows if r["aligned_observations"]]
    weights = [r["aligned_observations"] for r in known]
    for key in ("top1", "candidate_miss"):
        summary[f"weighted_{key}"] = float(np.average([r[key] for r in known], weights=weights))
    summary["sequence_quantiles"] = np.quantile([r["sequence_f1"] for r in rows],
                                              [0, .25, .5, .75, 1]).tolist()
    return summary


def run(data, output):
    artifact = Path("artifacts/pathsnap.joblib")
    historical = [Path("results") / name for name in
                  ("decoder.json", "models.json", "alignment.json", "protocol.json")]
    identifiers = {str(p): digest(p) for p in [artifact, *historical]}
    bundle = joblib.load(artifact)
    base = DecoderConfig(**bundle["decoder"])
    model_settings = {key: bundle["model"].get_params()[key] for key in
                      ("max_depth", "min_samples_leaf", "random_state")}
    protocol = json.loads(historical[-1].read_text())
    paths = {p.name: p for p in trips(data, "train")}
    if len(paths) != 80:
        raise ValueError("Exactly 80 training trip directories are required")
    keys = np.array(sorted(paths))
    folds = [dict(fit=keys[fit].tolist(), validation=keys[val].tolist())
             for fit, val in GroupKFold(3).split(keys, groups=keys)]
    if folds != protocol["folds"]:
        raise ValueError("Training trips must match the original grouped protocol")
    assert sorted(key for fold in folds for key in fold["validation"]) == list(keys)
    output.mkdir(parents=True, exist_ok=True)
    write(output / "protocol.json", dict(hashes=identifiers, fit_stride=protocol["fit_stride"], seed=SEED,
          folds=folds, decoder=asdict(base), model=model_settings,
          versions={name: version(name) for name in ("numpy", "scipy", "scikit-learn", "joblib")}))
    fits = {}
    models = []
    records = []
    for fold_id, fold in enumerate(folds):
        assert set(fold["fit"]).isdisjoint(fold["validation"])
        for key in fold["fit"]:
            if key in fits:
                continue
            trip = load_trip(paths[key])
            reference = load_reference(paths[key], trip)
            labels, _ = align_reference(trip, reference)
            sample = candidates(trip)
            step = protocol["fit_stride"]
            ids, labels = sample.ids[::step], labels[::step, None]
            mask = (ids >= 0) & (labels >= 0)
            fits[key] = (sample.features[::step][mask], (ids == labels)[mask])
        x, y = zip(*(fits[key] for key in fold["fit"]))
        model = make_model("decision_tree", model_settings).fit(np.concatenate(x), np.concatenate(y))
        models.append(model)
        joblib.dump(model, output / f"fold-{fold_id}.joblib")
        for key in fold["validation"]:
            trip = load_trip(paths[key])
            start = perf_counter()
            sample = candidates(trip)
            probabilities = score_candidates(model, sample)
            decoded = viterbi(trip, sample, probabilities, base)
            elapsed = perf_counter() - start
            diagnostics = {}
            traced = viterbi(trip, sample, probabilities, base, diagnostics=diagnostics)
            assert np.array_equal(decoded.points, traced.points) and decoded.legs == traced.legs
            # Held-out references are opened only after both predictions have finished.
            reference = load_reference(paths[key], trip)
            labels, _ = align_reference(trip, reference)
            records.append(dict(trip=key, fold=fold_id, seconds=elapsed) |
                           score(trip, sample, probabilities, decoded, reference, labels, diagnostics))
        print("Baseline fold", fold_id, flush=True)
    del fits
    baseline = summarize(records)
    write(output / "baseline.json", dict(summary=baseline, trips=records))
    print("Baseline", baseline, flush=True)

    # One change per trial, with geometry, transition and candidate hypotheses.
    trials = {
        "geometry_tighter": (replace(base, gps_sigma=22), 8),
        "geometry_looser": (replace(base, gps_sigma=55), 8),
        "transition_tighter": (replace(base, beta=8), 8),
        "transition_looser": (replace(base, beta=30), 8),
        "restart_cost_lower": (replace(base, break_penalty=5), 8),
        "restart_cost_higher": (replace(base, break_penalty=18), 8),
        "reach_higher": (replace(base, max_network_distance=650), 8),
        "gap_longer": (replace(base, max_gap=60), 8),
        "shortlist_12": (base, 12),
    }
    write(output / "search.json", {name: dict(decoder=asdict(cfg), shortlist=count)
                                    for name, (cfg, count) in trials.items()})
    rows = {name: [] for name in trials}
    for fold_id, (fold, model) in enumerate(zip(folds, models, strict=True)):
        for key in fold["validation"]:
            trip = load_trip(paths[key])
            samples, pending = {}, {}
            for name, (cfg, count) in trials.items():
                if count not in samples:
                    start = perf_counter()
                    sample = candidates(trip, count)
                    values = score_candidates(model, sample)
                    samples[count] = sample, values, perf_counter() - start
                sample, values, elapsed = samples[count]
                start = perf_counter()
                decoded = viterbi(trip, sample, values, cfg)
                pending[name] = (decoded, elapsed + perf_counter() - start)
            reference = load_reference(paths[key], trip)
            labels, _ = align_reference(trip, reference)
            for name, (_, count) in trials.items():
                decoded, seconds = pending[name]
                sample, values, _ = samples[count]
                rows[name].append(dict(trip=key, fold=fold_id, seconds=seconds) |
                                  score(trip, sample, values, decoded, reference, labels, {}))
        print("Trials fold", fold_id, flush=True)
    base_rows = {row["trip"]: row for row in records}
    comparisons = {}
    for name, result in rows.items():
        deltas = [r["sequence_f1"] - base_rows[r["trip"]]["sequence_f1"] for r in result]
        comparisons[name] = dict(summary=summarize(result), improved=sum(d > 1e-12 for d in deltas),
            worse=sum(d < -1e-12 for d in deltas), fold_deltas=[
                float(np.mean([d for r, d in zip(result, deltas) if r["fold"] == i])) for i in range(3)],
            trips=result)
    write(output / "trials.json", comparisons)
    write(output / "fold_artifacts.json", {p.name: digest(p) for p in sorted(output.glob("fold-*.joblib"))})
    assert all(digest(Path(p)) == sha for p, sha in identifiers.items())
    for name, item in comparisons.items():
        print(name, item["summary"], item["fold_deltas"], item["improved"], item["worse"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        run(args.data, args.output)
