"""Inventory both development partitions and generate reproducible exploration figures."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse.csgraph import connected_components

from data_processing.trips import DEVELOPMENT, load_reference, load_trip, trips
from features.candidates import candidates
from visualizations.maps import make_map


def inspect(directory, partition):
    trip = load_trip(directory, allow_missing=True)
    graph = trip.graph()
    good_nodes = np.isfinite(trip.nodes).all(axis=1)
    graph = graph[good_nodes][:, good_nodes]
    count, components = connected_components(graph, directed=False)
    sizes = np.bincount(components)
    gps = trip.track[trip.good]
    gaps = np.diff(trip.track[:, 2])
    arc_file = directory / f"{directory.name}.route"
    reference_rows, route_breaks, reference_error = None, None, None
    if arc_file.exists():
        with arc_file.open(encoding="utf-8") as file:
            reference_rows = sum(1 for _ in file)
        try:
            route = load_reference(directory, trip)
            edges = trip.arcs[route]
            route_breaks = int((edges[:-1, 1] != edges[1:, 0]).sum())
        except ValueError as error:
            reference_error = str(error)
    row = dict(partition=partition, trip_id=directory.name, gps_rows=len(trip.track),
               invalid_gps_rows=int((~trip.good).sum()), missing_gap_intervals=int(np.isnan(gaps).sum()),
               one_second_steps=int((gaps == 1).sum()), non_increasing_steps=int((gaps <= 0).sum()),
               irregular_positive_steps=int(((gaps > 0) & (gaps != 1)).sum()),
               steps_over_30_seconds=int((gaps > 30).sum()),
               max_gap_seconds=float(np.nanmax(gaps)) if np.isfinite(gaps).any() else None,
               west=float(gps[:, 0].min()) if len(gps) else None,
               south=float(gps[:, 1].min()) if len(gps) else None,
               east=float(gps[:, 0].max()) if len(gps) else None,
               north=float(gps[:, 1].max()) if len(gps) else None,
               nodes=len(trip.nodes), invalid_nodes=int((~good_nodes).sum()), arcs=len(trip.arcs),
               invalid_arcs=int((~trip.valid).sum()),
               directed_node_pairs=graph.nnz, weak_components=count,
               isolated_nodes=int(((graph.getnnz(axis=0) + graph.getnnz(axis=1)) == 0).sum()),
               largest_component=int(sizes.max(initial=0)), reference_rows=reference_rows,
               reference_breaks=route_breaks, reference_error=reference_error)
    for extension in ("track", "nodes", "arcs", "route"):
        file = directory / f"{directory.name}.{extension}"
        row[f"{extension}_bytes"] = file.stat().st_size if file.exists() else None
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inventory, summary = [], {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for partition, axis in zip(DEVELOPMENT, axes):
        directory = args.data / partition
        directories = sorted(path for path in directory.iterdir() if path.is_dir()) if directory.is_dir() else []
        if not directories:
            parser.error(f"No trips in {partition}")
        rows = [inspect(directory, partition) for directory in directories]
        inventory.extend(rows)
        summary[partition] = dict(trips=len(rows), observations=sum(r["gps_rows"] for r in rows),
                                  invalid_gps_rows=sum(r["invalid_gps_rows"] for r in rows),
                                  reference_breaks=sum(r["reference_breaks"] or 0 for r in rows),
                                  max_gap_seconds=max(r["max_gap_seconds"] or 0 for r in rows))
        axis.hist([r["gps_rows"] for r in rows], bins=12)
        axis.set(title=partition, xlabel="GPS rows per trip", ylabel="Trips")
        print(partition, summary[partition], flush=True)
    fig.savefig(args.output / "gps_counts.png")
    order = next((path for path in trips(args.data, "student_test")
                  if all((path / f"{path.name}.{ext}").is_file() for ext in ("nodes", "arcs"))), None)
    if order is None:
        parser.error("A student-test trip with GPS and road files is required to draw the map")
    trip = load_trip(order)
    reference = load_reference(order, trip) if (order / f"{order.name}.route").exists() else []
    near = np.unique(candidates(trip).ids[:, :3])
    make_map(trip, nearby=near, reference=reference).save(str(args.output / "student_eda_map.html"))
    fig, axis = plt.subplots(figsize=(8, 5), layout="constrained")
    from matplotlib.collections import LineCollection
    axis.add_collection(LineCollection(trip.xy[trip.arcs[near[near >= 0]]], colors="#8292a7", linewidths=.6))
    axis.scatter(*trip.gps[trip.good].T, s=2, color="#2859c5", label="GPS")
    axis.set(title=f"Student testing | {order.name}", xlabel="Easting (m)", ylabel="Northing (m)", aspect="equal")
    axis.legend()
    fig.savefig(args.output / "student_trajectory.png")
    with (args.output / "exploration.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(inventory[0]))
        writer.writeheader()
        writer.writerows(inventory)
    (args.output / "exploration.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
