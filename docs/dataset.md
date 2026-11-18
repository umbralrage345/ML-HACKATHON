# PathSnap raw development dataset

The team acquired the development data as the organiser-supplied `Student folder` package for the PES University PathSnap hackathon. The supplied **Dataset Exploration.pdf**, sections 2 and 3, describes the trip format. The **Main Guidelines.pdf** describes the challenge and split policy. The available materials do not identify the original GPS collection procedure, road-network producer, or reference-route generation procedure. The team organised and checked the supplied dataset.

## Layout and schema

Place the supplied package beside the repository, or pass its location with `--data`. Each trip directory uses its trip ID as the filename stem. All four raw formats are whitespace-delimited text without headers.

| File | Fields | How to interpret it |
| --- | --- | --- |
| `<trip_id>.track` | longitude, latitude, timestamp | Coordinates are in degrees and timestamps are in seconds. Rows preserve GPS observation order. |
| `<trip_id>.nodes` | longitude, latitude | The zero-based row index is the node ID within that trip's graph. |
| `<trip_id>.arcs` | from-node ID, to-node ID | Each row is a directed edge. Its zero-based row index is the arc ID. |
| `<trip_id>.route` | arc ID | Each row is one occurrence of an arc in the ordered reference route. It points into the arc file and has no one-to-one correspondence with GPS rows. |

The supplied package contains `train/<trip_id>/` and `student_test/<trip_id>/`. The official evaluator data is held separately. Keep raw files outside the public repository and use the original supplied package when reproducing the work.

| Partition | Trips | Raw files | GPS rows | Reference arc rows |
| --- | ---: | ---: | ---: | ---: |
| `train` | 80 | 320 | 208,417 | 31,336 |
| `student_test` | 10 | 40 | 19,160 | 3,477 |
| **Total** | **90** | **360** | **227,577** | **34,813** |

The inspected package contains 94,106,043 raw bytes. Every expected file was present and nonempty. The inventory detected zero invalid GPS, node, arc or reference rows and zero non-increasing GPS timestamp steps. Large positive GPS gaps are recorded and are valid input. The separate [exploration summary](../results/exploration.json) records 13 training and one student-test reference connectivity breaks. A route can reference valid arcs even when consecutive arcs lack a shared directed endpoint.

## Reproduce and demonstrate the inventory

From the repository root, use Python 3.13 as specified in the project README.

```bash
python -m data_processing.inspect_dataset --data "../Student folder" --output results/dataset_inventory.csv --strict
```

The [inventory CSV](../results/dataset_inventory.csv) contains trip IDs, row and error counts, geographic bounds, timestamp statistics, file sizes and one SHA-256 checksum per raw file. The hashes identify the exact bytes inspected and support integrity comparisons between team copies. They are locally computed fingerprints. Strict mode records findings and returns a nonzero exit code for unexpected split counts, duplicate trip IDs across partitions, missing or empty files, invalid rows or non-increasing timestamps.

For Review 1, open `train/00000001/` in the supplied package. Show a GPS row, then use an arc ID from `00000001.route` to look up its row in `00000001.arcs`. Follow that arc's two node IDs into `00000001.nodes`. Run the inventory and show the split counts and the corresponding CSV row.
