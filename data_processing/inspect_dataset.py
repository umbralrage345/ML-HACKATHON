"""Write a per-trip inventory of the supplied PathSnap development data."""

import argparse
import csv
import math
from pathlib import Path


def read_rows(path, width, convert):
    rows = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            fields = line.split()
            try:
                row = tuple(convert(field) for field in fields)
                rows.append(row if len(row) == width else None)
            except ValueError:
                rows.append(None)
    return rows


def valid_coordinates(row):
    return row is not None and -180 <= row[0] <= 180 and -90 <= row[1] <= 90


def inspect_trip(partition, directory):
    files = {ext: directory / f"{directory.name}.{ext}"
             for ext in ("track", "nodes", "arcs", "route")}
    track = read_rows(files["track"], 3, float)
    nodes = read_rows(files["nodes"], 2, float)
    arcs = read_rows(files["arcs"], 2, int)
    route = read_rows(files["route"], 1, int)
    valid_track = [row for row in track if valid_coordinates(row) and math.isfinite(row[2])]
    intervals = [current[2] - previous[2] for previous, current in zip(track, track[1:])
                 if previous is not None and current is not None
                 and math.isfinite(previous[2]) and math.isfinite(current[2])]
    valid_arc_ids = {index for index, arc in enumerate(arcs)
                     if arc is not None and all(
                         0 <= node < len(nodes) and valid_coordinates(nodes[node]) for node in arc
                     )}
    connected_nodes = {node for index in valid_arc_ids for node in arcs[index]}
    return {
        "partition": partition,
        "trip_id": directory.name,
        "gps_rows": len(track),
        "invalid_gps_rows": len(track) - len(valid_track),
        "node_rows": len(nodes),
        "invalid_node_rows": sum(not valid_coordinates(row) for row in nodes),
        "arc_rows": len(arcs),
        "invalid_arc_rows": len(arcs) - len(valid_arc_ids),
        "isolated_valid_nodes": sum(
            valid_coordinates(row) and index not in connected_nodes for index, row in enumerate(nodes)
        ),
        "reference_rows": len(route),
        "invalid_reference_rows": sum(row is None or row[0] not in valid_arc_ids for row in route),
        "non_increasing_steps": sum(interval <= 0 for interval in intervals),
        "one_second_steps": sum(interval == 1 for interval in intervals),
        "gps_steps_measured": len(intervals),
        "max_interval_seconds": max(intervals, default=None),
        "west": min((row[0] for row in valid_track), default=None),
        "east": max((row[0] for row in valid_track), default=None),
        "south": min((row[1] for row in valid_track), default=None),
        "north": max((row[1] for row in valid_track), default=None),
        **{f"{ext}_bytes": path.stat().st_size for ext, path in files.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("Student folder"))
    parser.add_argument("--output", type=Path, default=Path("dataset_inventory.csv"))
    args = parser.parse_args()
    rows = []
    for partition in ("train", "student_test"):
        directories = sorted(path for path in (args.data / partition).iterdir() if path.is_dir())
        if not directories:
            parser.error(f"No trips found under {args.data / partition}")
        print(f"{partition}: {len(directories)} trips")
        rows.extend(inspect_trip(partition, directory) for directory in directories)
    with args.output.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} trip records to {args.output}")


if __name__ == "__main__":
    main()
