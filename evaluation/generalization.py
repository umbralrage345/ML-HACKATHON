"""Measure apparent and held-out macro F1 on the recorded trip folds."""
import argparse
import json
from pathlib import Path

from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits

from training.experiment import data, flatten, save_json
from training.models import make_model


def run(cache, output):
    models = json.loads((output / "models.json").read_text())
    protocol = json.loads((output / "protocol.json").read_text())
    train = data(cache, "train", 80)
    results = {name: [] for name in models}
    with threadpool_limits(limits=2):
        for fold in protocol["folds"]:
            assert set(fold["fit"]).isdisjoint(fold["validation"])
            x, y = flatten(train, fold["fit"], protocol["fit_stride"])
            vx, vy = flatten(train, fold["validation"])
            for name, record in models.items():
                model = make_model(record["model"], record["config"]).fit(x, y)
                score = lambda a, b: f1_score(b, model.predict_proba(a)[:, 1] >= .5,
                                              average="macro", labels=[0, 1])
                results[name].append(dict(fit_macro_f1=score(x, y), validation_macro_f1=score(vx, vy)))
                print(name, results[name][-1], flush=True)
    for name, folds in results.items():
        for trial, expected in zip(folds, models[name]["cv_folds"], strict=True):
            assert abs(trial["validation_macro_f1"] - expected) < 1e-9
    save_json(output / "generalization.json", results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/candidates"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    run(args.cache, args.output)
