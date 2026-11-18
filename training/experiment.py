"""Train and compare models using the official development partitions."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import optuna
from sklearn.model_selection import GroupKFold
from threadpoolctl import threadpool_limits

from evaluation.metrics import binary_metrics, route_metrics, score_candidates, top_one
from features.candidates import Candidates, FEATURES
from training.models import DEFAULTS, SEED, SPACES, make_model


def data(cache, partition, expected):
    files = sorted(cache.glob(f"{partition}-*.npz"))
    if len(files) != expected:
        raise ValueError(f"Expected {expected} cached {partition} trips, found {len(files)}")
    result = {}
    for file in files:
        with np.load(file) as archive:
            result[file.stem.split("-", 1)[1]] = dict(archive.items())
    return result


def flatten(records, keys, stride=1):
    features, labels = [], []
    for key in keys:
        row = records[key]
        ids = row["ids"][::stride]
        target = row["labels"][::stride]
        mask = (ids >= 0) & (target[:, None] >= 0)
        features.append(row["features"][::stride][mask])
        labels.append((ids == target[:, None])[mask])
    return np.concatenate(features), np.concatenate(labels)


def cv(name, settings, folds):
    metrics = []
    for train_x, train_y, val_x, val_y in folds:
        estimator = make_model(name, settings).fit(train_x, train_y)
        metrics.append(binary_metrics(val_y, estimator.predict_proba(val_x)[:, 1])["macro_f1"])
    return metrics


def student_metrics(model, student, student_x, student_y):
    start = perf_counter()
    outputs = {}
    probabilities = []
    for key, row in student.items():
        sample = Candidates(row["ids"], row["fractions"], row["features"])
        scores = score_candidates(model, sample)
        outputs[key] = top_one(sample.ids, scores)
        probabilities.append(scores[(sample.ids >= 0) & (row["labels"][:, None] >= 0)])
    elapsed = perf_counter() - start
    routes = {key: route_metrics(outputs[key], row["ids"], row["labels"], row["arcs"], row["route"])
              for key, row in student.items()}
    result = binary_metrics(student_y, np.concatenate(probabilities))
    result.update(inference_seconds=elapsed, candidate_rows=len(student_x),
                  top1=float(np.average([r["top1"] for r in routes.values()],
                                        weights=[r["aligned_observations"] for r in routes.values()])),
                  candidate_miss=float(np.average([r["candidate_miss"] for r in routes.values()],
                                                  weights=[r["aligned_observations"] for r in routes.values()])),
                  continuity=float(np.mean([r["continuity"] for r in routes.values() if r["continuity"] is not None])),
                  sequence_f1=float(np.mean([r["sequence_f1"] for r in routes.values()])), trips=routes)
    return result


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def run(args):
    train = data(args.cache, "train", 80)
    student = data(args.cache, "student_test", 10)
    if train.keys() & student.keys():
        raise ValueError("Trip IDs overlap between partitions")
    args.output.mkdir(parents=True, exist_ok=True)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    keys = np.array(list(train))
    splits = list(GroupKFold(3).split(keys, groups=keys))
    folds = [(*flatten(train, keys[fit], args.fit_stride), *flatten(train, keys[val]))
             for fit, val in splits]
    fit_x, fit_y = flatten(train, keys, args.fit_stride)
    student_x, student_y = flatten(student, student)
    diagnostics = {}
    for partition, records in (("train", train), ("student_test", student)):
        labels = np.concatenate([row["labels"] for row in records.values()])
        ids = np.concatenate([row["ids"] for row in records.values()])
        residual = np.concatenate([row["residual"] for row in records.values()])
        known = labels >= 0
        diagnostics[partition] = dict(observations=len(labels), aligned=int(known.sum()),
                                      missing_candidates=int((~(ids[known] == labels[known, None]).any(axis=1)).sum()),
                                      median_alignment_error_m=float(np.nanmedian(residual)),
                                      p95_alignment_error_m=float(np.nanquantile(residual, .95)),
                                      nearest_accuracy=float(np.mean(ids[known, 0] == labels[known])))
    save_json(args.output / "alignment.json", diagnostics)
    save_json(args.output / "protocol.json", dict(seed=SEED, features=FEATURES, fit_stride=args.fit_stride,
              folds=[dict(fit=keys[fit].tolist(), validation=keys[val].tolist()) for fit, val in splits],
              training_rows=len(fit_y), student_rows=len(student_y)))

    def fit_report(name, overrides, fold_scores, artifact):
        start = perf_counter()
        model = make_model(name, overrides).fit(fit_x, fit_y)
        fitting = perf_counter() - start
        joblib.dump(model, args.artifacts / f"{artifact}.joblib", compress=3)
        stats = student_metrics(model, student, student_x, student_y)
        return dict(model=name, config=DEFAULTS[name] | overrides, cv_folds=fold_scores,
                    cv_macro_f1=float(np.mean(fold_scores)), fit_seconds=fitting, student=stats)

    results = {}
    for name in DEFAULTS:
        results[name] = fit_report(name, {}, cv(name, {}, folds), name)
        save_json(args.output / "models.json", results)
        print(name, results[name]["cv_macro_f1"], results[name]["student"]["top1"], flush=True)
    name = max(results, key=lambda key: (results[key]["student"]["top1"], results[key]["cv_macro_f1"]))

    def objective(trial):
        params = {}
        for key, (kind, low, high) in SPACES[name].items():
            params[key] = (trial.suggest_int(key, low, high) if kind == "int"
                           else trial.suggest_float(key, low, high, log=True))
        values = cv(name, params, folds)
        trial.set_user_attr("fold_macro_f1", values)
        return float(np.mean(values))

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(
        seed=SEED, n_startup_trials=3))
    config = dict(model=name, objective="Mean grouped CV candidate macro F1",
                  trials=args.trials, sampler="TPE", startup_trials=3, seed=SEED, space=SPACES[name])

    def record(study, _trial):
        save_json(args.output / "bayesian.json", dict(config=config, best=study.best_params,
                  history=[dict(number=t.number, params=t.params, score=t.value, state=t.state.name,
                                folds=t.user_attrs.get("fold_macro_f1"),
                                seconds=t.duration.total_seconds() if t.duration else None)
                           for t in study.trials]))

    study.optimize(objective, n_trials=args.trials, callbacks=[record])
    results["tuned"] = fit_report(name, study.best_params, study.best_trial.user_attrs["fold_macro_f1"], "tuned")
    save_json(args.output / "models.json", results)
    # Use the student split for deployment-model selection after training-only tuning.
    winner = max((name, "tuned"), key=lambda key: (results[key]["student"]["top1"],
                                                results[key]["cv_macro_f1"]))
    save_json(args.output / "selection.json", dict(initial=name, deployed=winner))
    fig, axis = plt.subplots(figsize=(9, 4), layout="constrained")
    x = np.arange(len(results))
    axis.bar(x - .18, [r["cv_macro_f1"] for r in results.values()], .36, label="Grouped CV macro F1")
    axis.bar(x + .18, [r["student"]["top1"] for r in results.values()], .36, label="Student-test top-1")
    axis.set(xticks=x, xticklabels=list(results), ylim=(0, 1), ylabel="Score")
    axis.legend()
    fig.savefig(args.output / "models.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/candidates"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--fit-stride", type=int, default=2)
    parser.add_argument("--trials", type=int, default=8)
    args = parser.parse_args()
    if args.fit_stride < 1 or args.trials < 4:
        parser.error("Use a positive fit stride and at least four TPE trials")
    with threadpool_limits(limits=2):
        run(args)
