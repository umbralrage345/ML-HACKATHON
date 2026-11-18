"""Directed network transitions and log-space Viterbi decoding."""
from dataclasses import dataclass
from functools import lru_cache
from heapq import heappop, heappush

import numpy as np


@dataclass(frozen=True)
class DecoderConfig:
    beta: float = 30.
    gps_sigma: float = 35.
    max_gap: float = 30.
    max_network_distance: float = 450.
    break_penalty: float = 10.


@dataclass
class Decoded:
    points: np.ndarray
    legs: list[list[int]]

    @property
    def route(self):
        return [arc for leg in self.legs for arc in leg]


class RoadRouter:
    def __init__(self, trip, limit):
        self.trip = trip
        self.limit = limit
        self.adjacency = {}
        for arc in np.flatnonzero(trip.valid):
            a, b = trip.arcs[arc]
            self.adjacency.setdefault(a, []).append((b, trip.length[arc], int(arc)))
        # Cache is per trip and shared while comparing decoder settings.
        self.paths = lru_cache(maxsize=4096)(self._paths)

    def _paths(self, start):
        distances, parent = {start: 0.}, {}
        heap = [(0., start)]
        while heap:
            distance, node = heappop(heap)
            if distance != distances[node]:
                continue
            for target, length, arc in self.adjacency.get(node, ()):
                total = distance + length
                if total <= self.limit and total < distances.get(target, np.inf):
                    distances[target] = total
                    parent[target] = (node, arc)
                    heappush(heap, (total, target))
        return distances, parent

    def bridge(self, left, right):
        source, target = self.trip.arcs[left, 1], self.trip.arcs[right, 0]
        _, parent = self.paths(source)
        arcs = []
        while target != source:
            if target not in parent:
                return None
            target, arc = parent[target]
            arcs.append(arc)
        return arcs[::-1]

    def transitions(self, left, right, x, y, observed, elapsed, config):
        trip = self.trip
        matrix = np.full((len(left), len(right)), -np.inf)
        maximum = min(config.max_network_distance, max(70., elapsed * 65.))
        for i, arc in enumerate(left):
            if arc < 0:
                continue
            source = trip.arcs[arc, 1]
            distances, _ = self.paths(source)
            for j, target in enumerate(right):
                if target < 0:
                    continue
                if arc == target:
                    progress = (y[j] - x[i]) * trip.length[arc]
                    length = abs(progress)
                    reverse = max(0., -progress - 12.) / config.beta
                else:
                    length = ((1 - x[i]) * trip.length[arc] +
                              distances.get(trip.arcs[target, 0], np.inf) + y[j] * trip.length[target])
                    reverse = 0.
                if length <= maximum:
                    matrix[i, j] = -abs(length - observed) / config.beta - reverse
        return matrix


def viterbi(trip, sample, probabilities, config=DecoderConfig(), router=None, *, diagnostics=None):
    router = router or RoadRouter(trip, config.max_network_distance)
    ids = sample.ids
    emission = (np.log(np.clip(probabilities, 1e-5, 1)) -
                .5 * (sample.features[:, :, 0] / config.gps_sigma) ** 2)
    emission[ids < 0] = -np.inf
    result = np.full(len(ids), -1)
    reset = np.ones(len(ids), dtype=bool)
    previous_scores = np.empty(ids.shape[1])
    parents = np.full(ids.shape, -1, dtype=int)
    breaks = np.ones(ids.shape, dtype=bool)
    if diagnostics is not None:
        diagnostics.update(gap_resets=0, invalid_time_resets=0, missing_previous_resets=0,
                           disconnected_transitions=0, blocked_transition_steps=0,
                           selected_transition_restarts=0, intermediate_arcs=0)
        attempted = np.zeros(len(ids), dtype=bool)
    slot = -1
    for i, row in enumerate(ids):
        if not (row >= 0).any():
            continue
        elapsed = trip.track[i, 2] - trip.track[i - 1, 2] if i else 0
        if i and (ids[i - 1] >= 0).any() and 0 < elapsed <= config.max_gap:
            displacement = np.linalg.norm(trip.gps[i] - trip.gps[i - 1])
            matrix = router.transitions(ids[i - 1], row, sample.fractions[i - 1],
                                        sample.fractions[i], displacement, elapsed, config)
            if diagnostics is not None:
                attempted[i] = True
                previous = ids[i - 1][ids[i - 1] >= 0]
                current = row[row >= 0]
                for arc in previous:
                    distances, _ = router.paths(trip.arcs[arc, 1])
                    diagnostics["disconnected_transitions"] += sum(
                        arc != candidate and trip.arcs[candidate, 0] not in distances
                        for candidate in current)
                diagnostics["blocked_transition_steps"] += int(not np.isfinite(matrix).any())
            scores = matrix + previous_scores[:, None]
            best = np.argmax(scores, axis=0)
            linked = scores[best, np.arange(len(row))]
            fallback = int(np.argmax(previous_scores))
            disconnected = linked < previous_scores[fallback] - config.break_penalty
            parents[i] = np.where(disconnected, fallback, best)
            breaks[i] = disconnected
            previous_scores = emission[i] + np.where(
                disconnected, previous_scores[fallback] - config.break_penalty, linked)
        else:
            previous_scores = emission[i]
            if diagnostics is not None and i:
                reason = ("missing_previous_resets" if not (ids[i - 1] >= 0).any() else
                          "gap_resets" if elapsed > config.max_gap else "invalid_time_resets")
                diagnostics[reason] += 1
        # Keep row scores bounded without changing the argmax.
        previous_scores -= np.max(previous_scores)
        result[i] = int(np.argmax(previous_scores))
    for i in range(len(ids) - 1, -1, -1):
        if result[i] < 0:
            slot = -1
            continue
        if slot < 0:
            slot = result[i]
        reset[i] = breaks[i, slot]
        result[i] = ids[i, slot]
        slot = parents[i, slot]
    legs = []
    if diagnostics is not None:
        diagnostics["selected_transition_restarts"] = int((attempted & reset & (result >= 0)).sum())
    last = -1
    for i, arc in enumerate(result):
        if arc < 0:
            last = -1
            continue
        if reset[i] or last < 0:
            legs.append([int(arc)])
        elif last != arc:
            bridge = router.bridge(last, arc)
            if bridge is None:
                legs.append([int(arc)])
            else:
                legs[-1].extend([*bridge, int(arc)])
                if diagnostics is not None:
                    diagnostics["intermediate_arcs"] += len(bridge)
        last = arc
    return Decoded(result, legs)
