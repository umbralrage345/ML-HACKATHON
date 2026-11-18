"""Five candidate probability models and their Bayesian search spaces."""
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

SEED = 42
# Log-scale ranges cover orders of magnitude in regularization and learning rate.
SPACES = {
    "logistic": {"C": ("log", .01, 30.)},
    "naive_bayes": {"var_smoothing": ("log", 1e-10, 1e-2)},
    "decision_tree": {"max_depth": ("int", 4, 18), "min_samples_leaf": ("int", 12, 130)},
    "extra_trees": {"max_depth": ("int", 8, 22), "min_samples_leaf": ("int", 8, 100)},
    "hist_gradient": {"learning_rate": ("log", .03, .25), "max_leaf_nodes": ("int", 15, 47),
                      "min_samples_leaf": ("int", 15, 100), "l2_regularization": ("log", .001, 5.)},
}
DEFAULTS = {
    "logistic": dict(C=1., max_iter=200, random_state=SEED),
    "naive_bayes": dict(var_smoothing=1e-9),
    "decision_tree": dict(max_depth=12, min_samples_leaf=35, random_state=SEED),
    "extra_trees": dict(n_estimators=28, max_depth=16, min_samples_leaf=25, random_state=SEED, n_jobs=2),
    "hist_gradient": dict(max_iter=75, max_leaf_nodes=23, learning_rate=.12, min_samples_leaf=30,
                         l2_regularization=0., early_stopping=False, random_state=SEED),
}


def make_model(name, settings=None):
    params = DEFAULTS[name] | (settings or {})
    if name == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(**params))
    if name == "naive_bayes":
        return make_pipeline(StandardScaler(), GaussianNB(**params))
    return {"decision_tree": DecisionTreeClassifier, "extra_trees": ExtraTreesClassifier,
            "hist_gradient": HistGradientBoostingClassifier}[name](**params)
