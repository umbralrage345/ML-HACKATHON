"""Load inference inputs independently of the optional reference route."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix

from data_processing.inspect_dataset import read_rows, valid_coordinates

DEVELOPMENT = ("train", "student_test")


def trips(root: Path, partition: str) -> list[Path]:
    return sorted(p.parent for p in (root / partition).glob("*/*.track")
                  if p.stem == p.parent.name)


def raw(directory, extension, width, convert, optional=False):
    path = directory / f"{directory.name}.{extension}"
    if optional and not path.is_file():
        return []
    return read_rows(path, width, convert)


@dataclass
class Trip:
    track: np.ndarray
    nodes: np.ndarray
    arcs: np.ndarray
    valid: np.ndarray
    xy: np.ndarray
    gps: np.ndarray
    length: np.ndarray

    @property
    def good(self):
        return np.isfinite(self.track).all(axis=1)

    def graph(self):
        # Collapse duplicate directed node pairs to their minimum length.
        edges = {}
        for (a, b), length in zip(self.arcs[self.valid], self.length[self.valid]):
            edges[a, b] = min(length, edges.get((a, b), np.inf))
        a, b = zip(*edges) if edges else ([], [])
        return coo_matrix((list(edges.values()), (a, b)),
                          shape=(len(self.nodes), len(self.nodes))).tocsr()


def load_trip(directory: Path, *, allow_missing: bool = False) -> Trip:
    rows = raw(directory, "track", 3, float, allow_missing)
    track = np.array([r if valid_coordinates(r) and np.isfinite(r[2])
                      else (np.nan,) * 3 for r in rows], dtype=float).reshape(-1, 3)
    rows = raw(directory, "nodes", 2, float, allow_missing)
    nodes = np.array([r if valid_coordinates(r) else (np.nan,) * 2 for r in rows],
                     dtype=float).reshape(-1, 2)
    rows = raw(directory, "arcs", 2, int, allow_missing)
    arcs = np.array([r if r and all(0 <= i < len(nodes) for i in r)
                     else (-1, -1) for r in rows], dtype=int).reshape(-1, 2)
    valid = (arcs >= 0).all(axis=1)
    valid[valid] = np.isfinite(nodes[arcs[valid]]).all(axis=(1, 2))
    usable = nodes[np.isfinite(nodes).all(axis=1)]
    origin = usable.mean(axis=0) if len(usable) else np.zeros(2)
    # Local equirectangular projection, in metres, centred on the road network.
    scale = np.radians(1) * 6371008.8 * np.array([np.cos(np.radians(origin[1])), 1])
    xy = (nodes - origin) * scale
    gps = (track[:, :2] - origin) * scale
    length = np.zeros(len(arcs))
    length[valid] = np.linalg.norm(np.diff(xy[arcs[valid]], axis=1)[:, 0], axis=1)
    return Trip(track, nodes, arcs, valid, xy, gps, length)


def load_reference(directory: Path, trip: Trip) -> np.ndarray:
    rows = raw(directory, "route", 1, int)
    if not rows or any(r is None or not 0 <= r[0] < len(trip.arcs)
                       or not trip.valid[r[0]] for r in rows):
        raise ValueError(f"Invalid reference route for {directory.name}")
    return np.array([r[0] for r in rows])
