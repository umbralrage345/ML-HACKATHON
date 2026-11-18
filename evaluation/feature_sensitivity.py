"""Measure held-out feature sensitivity for the deployed classifier."""
import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.inspection import permutation_importance
from threadpoolctl import threadpool_limits

from features.candidates import FEATURES
from training.experiment import data, flatten, save_json
from training.models import SEED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=Path("artifacts/candidates"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    records = data(args.cache, "student_test", 10)
    x, y = flatten(records, records)
    name = json.loads((args.output / "selection.json").read_text())["deployed"]
    model = joblib.load(args.artifacts / f"{name}.joblib")
    with threadpool_limits(limits=2):
        changes = permutation_importance(model, x, y, scoring="f1_macro",
                                         n_repeats=3, random_state=SEED)
    ordered = np.argsort(changes.importances_mean)
    features = [FEATURES[i] for i in ordered]
    save_json(args.output / "feature_sensitivity.json", dict(
        partition="student_test", artifact=name, scoring="candidate macro F1", repeats=3, seed=SEED,
        changes={name: changes.importances[i].tolist() for i, name in enumerate(FEATURES)}))
    fig, axis = plt.subplots(figsize=(8, 5), layout="constrained")
    axis.barh(features, changes.importances_mean[ordered], xerr=changes.importances_std[ordered])
    axis.set(xlabel="Decrease in candidate macro F1 after permutation", title="Student-test feature sensitivity")
    fig.savefig(args.output / "feature_sensitivity.png")


if __name__ == "__main__":
    main()
