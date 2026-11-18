"""Spatial shortlist and inference-time features in projected metres."""
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

FEATURES = ("distance", "start_distance", "end_distance", "fraction", "length",
            "heading_cosine", "interval", "speed", "rank", "distance_over_best",
            "incoming_degree", "outgoing_degree")


@dataclass
class Candidates:
    ids: np.ndarray
    fractions: np.ndarray
    features: np.ndarray


def project(points, start, end):
    vector = end - start
    delta = points - start
    squared = np.sum(vector ** 2, axis=-1)
    fraction = np.clip(np.sum(delta * vector, axis=-1) / np.maximum(squared, 1e-12), 0, 1)
    distance = np.linalg.norm(delta - fraction[..., None] * vector, axis=-1)
    return distance, fraction


def candidates(trip, count=8):
    ids = np.full((len(trip.track), count), -1)
    fractions = np.zeros(ids.shape)
    features = np.zeros((*ids.shape, len(FEATURES)), dtype=np.float32)
    road_ids = np.flatnonzero(trip.valid)
    observations = np.flatnonzero(trip.good)
    if not (len(road_ids) and len(observations)):
        return Candidates(ids, fractions, features)
    edges = trip.arcs[road_ids]
    a, b = trip.xy[edges].transpose(1, 0, 2)
    # Include interiors of long segments, so the shortlist is not endpoint-biased.
    n = np.maximum(1, np.ceil(trip.length[road_ids] / 35).astype(int))
    owner = np.repeat(np.arange(len(edges)), n)
    index = np.arange(len(owner)) - np.repeat(np.cumsum(n) - n, n)
    samples = a[owner] + ((index + .5) / n[owner])[:, None] * (b - a)[owner]
    tree = cKDTree(samples)
    indegree = np.bincount(edges[:, 1], minlength=len(trip.nodes))
    outdegree = np.bincount(edges[:, 0], minlength=len(trip.nodes))
    previous = np.maximum(observations - 1, 0)
    delta = trip.gps[observations] - trip.gps[previous]
    dt = trip.track[observations, 2] - trip.track[previous, 2]
    timed = (dt > 0) & (dt <= 30)
    speed = np.divide(np.linalg.norm(delta, axis=1), dt, out=np.zeros(len(dt)), where=timed)
    direction = np.nan_to_num(delta / np.maximum(np.linalg.norm(delta, axis=1)[:, None], 1))
    direction[~timed] = 0
    for offset in range(0, len(observations), 1024):
        block = slice(offset, offset + 1024)
        rows = observations[block]
        points = trip.gps[rows, None]
        _, nearby = tree.query(points[:, 0], k=list(range(1, min(64, len(samples)) + 1)))
        near = np.sort(owner[nearby], axis=1)
        distance, fraction = project(points, a[near], b[near])
        distance[:, 1:][near[:, 1:] == near[:, :-1]] = np.inf
        ranking = np.argsort(distance, axis=1, kind="stable")[:, :count]
        selected = np.take_along_axis(near, ranking, axis=1)
        dist = np.take_along_axis(distance, ranking, axis=1)
        frac = np.take_along_axis(fraction, ranking, axis=1)
        width = ranking.shape[1]
        length = trip.length[road_ids[selected]]
        heading = np.sum(direction[block, None] * (b - a)[selected], axis=-1)
        slots = (len(rows), width)
        data = np.stack([
            dist, np.linalg.norm(points - a[selected], axis=-1),
            np.linalg.norm(points - b[selected], axis=-1), frac, length,
            heading / np.maximum(length, 1), np.broadcast_to(np.where(timed, dt, 0)[block, None], slots),
            np.broadcast_to(speed[block, None], slots), np.broadcast_to(np.arange(width), slots),
            dist - dist[:, :1], indegree[edges[selected, 0]], outdegree[edges[selected, 1]],
        ], axis=-1)
        usable = np.isfinite(dist)
        ids[rows, :width] = np.where(usable, road_ids[selected], -1)
        fractions[rows, :width] = np.where(usable, frac, 0)
        features[rows, :width] = np.where(usable[..., None], data, 0)
    return Candidates(ids, fractions, features)
