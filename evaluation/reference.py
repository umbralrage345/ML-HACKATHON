"""Infer observation labels from ordered reference positions for scoring and fitting."""
import numpy as np

from features.candidates import project


def align_reference(trip, route, maximum_error=75.0):
    rows = np.flatnonzero(trip.good)
    labels = np.full(len(trip.track), -1)
    residual = np.full(len(labels), np.nan)
    if not len(rows):
        return labels, residual
    a, b = trip.xy[trip.arcs[route]].transpose(1, 0, 2)
    positions = np.arange(len(route), dtype=np.int32)
    back = np.empty((len(rows), len(route)), dtype=np.int32)
    # A weak skip cost discourages forward jumps between repeated road IDs.
    progress = positions * 2.0
    cost = positions * 8.0
    for i, row in enumerate(rows):
        adjusted = cost - progress
        prefix = np.minimum.accumulate(adjusted)
        best = np.maximum.accumulate(np.where(adjusted == prefix, positions, 0))
        distance, _ = project(trip.gps[row], a, b)
        jump = np.r_[np.inf, prefix[:-1] + progress[1:] + 3]
        advance = jump < cost
        cost = np.minimum(cost, jump) + np.minimum(distance, 150)
        back[i] = np.where(advance, np.r_[0, best[:-1]], positions)

    # Symmetric weak penalty for leaving the end of the reference unvisited.
    j = int(np.argmin(cost + (positions[-1] - positions) * 8.0))
    for i in range(len(rows) - 1, -1, -1):
        row = rows[i]
        distance, _ = project(trip.gps[row], a[j], b[j])
        residual[row] = distance
        if distance <= maximum_error:
            labels[row] = route[j]
        j = back[i, j]
    return labels, residual
