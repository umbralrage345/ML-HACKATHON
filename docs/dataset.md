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

The supplied package contains `train/<trip_id>/` and `student_test/<trip_id>/`. The official evaluator data is held separately. Keep the supplied package outside Git. Do not commit the 94 MB raw dataset unless the team has a specific reason and permission to distribute it. Training trips are used to fit and tune the model. Student-test trips are held out to measure performance on trips the model did not train on.

| Partition | Trips | Raw files | GPS rows | Reference arc rows |
| --- | ---: | ---: | ---: | ---: |
| `train` | 80 | 320 | 208,417 | 31,336 |
| `student_test` | 10 | 40 | 19,160 | 3,477 |
| **Total** | **90** | **360** | **227,577** | **34,813** |

The inspected package contains 94,106,043 raw bytes. Every expected file was present and nonempty. The inventory detected zero invalid GPS, node, arc or reference rows and zero non-increasing GPS timestamp steps. Large positive GPS gaps are recorded and are valid input. A route can reference valid arcs even when consecutive arcs lack a shared directed endpoint.

## Reproduce and demonstrate the inventory

From the repository root, use Python 3.13.

```bash
python -m data_processing.inspect_dataset --data "../Student folder" --output results/dataset_inventory.csv --strict
```

The [inventory CSV](../results/dataset_inventory.csv) contains trip IDs, row and error counts, geographic bounds, timestamp statistics, file sizes and one SHA-256 checksum per raw file. The hashes identify the exact bytes inspected and support integrity comparisons between team copies. They are locally computed fingerprints. Strict mode records findings and returns a nonzero exit code for unexpected split counts, duplicate trip IDs across partitions, missing or empty files, invalid rows or non-increasing timestamps.

## Review 1 demonstration

1. Open the externally supplied `Student folder`.
2. Show the `train` and `student_test` directories.
3. Open `train/00000001/`.
4. Show `00000001.track`, `00000001.nodes`, `00000001.arcs` and `00000001.route`. The first route entry, arc ID `2641`, is on editor line `2642` of the arc file. It points from node `1584` to node `32308`, whose coordinates are on editor lines `1585` and `32309` of the node file.
5. Run the inventory command above.
6. Open `results/dataset_inventory.csv` and show the row for trip `00000001`.
7. Explain that the script checks each expected filename and byte size, reads GPS rows, counts invalid records separately, and verifies the split counts. A missing file means the expected path is absent. An empty file means the path exists and contains zero bytes. A malformed row can also make a present file unusable.

## Questions to prepare for

| Question | Answer |
| --- | --- |
| Where did the data come from? Did your team collect it? | The organisers supplied the original package. The team investigated, verified and prepared it. The original collection process is undocumented in the available materials. |
| How many trips are available? | 90 development trips, split into 80 training and 10 student-test trips. |
| What is the difference between a node and an arc? | A node is a location in the road graph. An arc is a directed connection between two nodes. |
| How do you find an arc ID? | Use the zero-based row index in the arc file. When jumping to that row in a one-based editor, add one. |
| Why do you need the route file? | It gives the ordered reference journey, which supports training label preparation and evaluation. |
| Why don't GPS rows correspond directly to road-network rows? | A GPS row is a timed observation. Road-network rows describe fixed graph locations and connections. Several observations can fall along one arc, and some arcs can occur between GPS observations. |
