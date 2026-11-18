"""Candidate, observation and chronological arc-sequence metrics."""
import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, log_loss,
                             precision_score, recall_score)


def top_one(ids, scores):
    result = np.full(len(ids), -1)
    rows = (ids >= 0).any(axis=1)
    selected = np.where(ids >= 0, scores, -np.inf).argmax(axis=1)
    result[rows] = ids[np.arange(len(ids))[rows], selected[rows]]
    return result


def score_candidates(model, sample):
    mask = sample.ids >= 0
    scores = np.zeros(mask.shape)
    if mask.any():
        scores[mask] = model.predict_proba(sample.features[mask])[:, 1]
    return scores


def binary_metrics(y, probabilities):
    pred = probabilities >= .5
    return dict(accuracy=accuracy_score(y, pred),
                precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred, zero_division=0),
                macro_f1=f1_score(y, pred, average="macro", labels=[0, 1], zero_division=0),
                confusion_matrix=confusion_matrix(y, pred, labels=[0, 1]).tolist(),
                log_loss=log_loss(y, np.clip(probabilities, 1e-9, 1 - 1e-9), labels=[0, 1]))


def consecutive_unique(sequence):
    result = []
    for value in sequence:
        if value >= 0 and (not result or result[-1] != value):
            result.append(int(value))
    return result


def sequence_f1(predicted, reference):
    # Bit-parallel longest common subsequence; reference occurrences retain order.
    masks = {}
    for index, arc in enumerate(reference):
        masks[arc] = masks.get(arc, 0) | (1 << index)
    state = 0
    for arc in predicted:
        matches = masks.get(arc, 0) | state
        state = matches & ~(matches - ((state << 1) | 1))
    return 2 * state.bit_count() / max(len(predicted) + len(reference), 1)


def route_metrics(pred, ids, labels, arcs, route, reconstructed=None):
    known = labels >= 0
    left, right = pred[:-1], pred[1:]
    pairs = (left >= 0) & (right >= 0)
    connected = (left[pairs] == right[pairs]) | (arcs[left[pairs], 1] == arcs[right[pairs], 0])
    return dict(aligned_observations=int(known.sum()), observations=len(ids),
                top1=float(np.mean(pred[known] == labels[known])) if known.any() else None,
                candidate_miss=float(np.mean(~(ids[known] == labels[known, None]).any(axis=1)))
                if known.any() else None,
                continuity=float(connected.mean()) if len(connected) else None,
                continuity_pairs=int(pairs.sum()),
                sequence_f1=sequence_f1(consecutive_unique(pred if reconstructed is None else reconstructed),
                                        consecutive_unique(route)))
