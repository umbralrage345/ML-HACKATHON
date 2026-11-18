# Individual Contribution Record — Member 1: Dataset Inventory and Integrity

> **Complete the placeholders and remove any statement that does not match the work you personally performed.** This record describes the agreed Member 1 workstream; it must be checked against the actual branch diff before submission.

## Contributor details

| Field | Entry |
|---|---|
| Contributor | `[Full name]` |
| GitHub username | `[GitHub username]` |
| Student ID / SRN | `[Include only if required by the course or event]` |
| Assigned branch | `feat/member-1-dataset` |
| Contribution period | `[Start date – end date]` |
| Pull request | `[PR URL]` |
| Main contribution commits | `[Commit hashes / links]` |

## Contribution summary

Member 1's allocated responsibility was to establish a reliable understanding of the organiser-provided PathSnap dataset before it was used by the preprocessing and modelling pipeline. This workstream covers dataset inventory, file-format inspection, provenance documentation, schema validation and basic integrity analysis.

The project consumes four related files per trip:

- `.track`: GPS observations containing longitude, latitude and timestamp.
- `.nodes`: road-network node coordinates, with row position serving as the node identifier.
- `.arcs`: directed road edges represented by source and destination node identifiers; row position serves as the arc identifier.
- `.route`: ordered reference arc IDs used for evaluation after prediction.

The original GPS trajectories were supplied by the organisers. The contribution is inspection and validation of this supplied data, not original data collection.

## Work personally performed

Complete this table with specific actions. Replace the examples with what the branch actually contains.

| Work area | What I personally did | Evidence / files |
|---|---|---|
| Dataset inventory | `[Record how you enumerated trips, files, sizes and record counts.]` | `[Exact file path / commit]` |
| Schema and format inspection | `[Record how you verified columns, types, identifiers and file relationships.]` | `[Exact file path / commit]` |
| Integrity checks | `[Record checks actually implemented, such as missing files, malformed rows, invalid coordinates, timestamp order, or node/arc references.]` | `[Exact file path / commit]` |
| Dataset provenance | `[Record how the supplied dataset, splits and source limitations were documented.]` | `[Exact file path / commit]` |
| Findings communicated | `[Record specific findings handed to the preprocessing/model team.]` | `[Issue, message, document or commit]` |

## Files owned or materially changed

The agreed branch allocation identified the following likely files. Keep only files that appear in your actual contribution and describe your changes precisely.

| File | Role in the workstream | My actual change |
|---|---|---|
| `data_processing/inspect_dataset.py` | Dataset inspection / inventory utility | `[Describe the functions or checks you implemented or changed.]` |
| `results/dataset_inventory.csv` | Generated inventory output | `[Describe how it was produced and validated.]` |
| `docs/dataset.md` | Dataset schema, provenance and limitations documentation | `[Confirm whether this file exists and describe your contribution.]` |
| Other: `[path]` | `[Purpose]` | `[Actual change]` |

## Technical approach

Describe the implementation in enough detail that another student can reproduce and explain it. Address only the points relevant to your work:

1. How the trip directories and four-file sets were discovered and paired.
2. How the whitespace-separated file formats were parsed and malformed records handled.
3. How row indices were interpreted as node IDs or arc IDs.
4. Which coordinate, timestamp, node-reference and arc-reference checks were performed.
5. How aggregate counts and anomalies were recorded.
6. How the inventory was made repeatable rather than manually assembled.

**Implementation details:**

`[Write your explanation here. Include relevant functions, assumptions, edge cases and any limitations.]`

## Verification and results

| Check | Command / method | Actual result | Evidence |
|---|---|---|---|
| Inventory generation | `[Command]` | `[Pass / fail and summary]` | `[Log / output / commit]` |
| Schema checks | `[Command]` | `[Observed result]` | `[Log / output / commit]` |
| Integrity checks | `[Command]` | `[Observed result]` | `[Log / output / commit]` |
| Repeatability | `[Command, rerun or comparison]` | `[Observed result]` | `[Log / output / commit]` |

Do not copy findings from another member's run unless you identify who ran them and how you independently verified them. Do not invent counts or test outcomes.

## Collaboration and handoff

`[Explain what dataset assumptions, schema information, anomalies or recommendations you handed to Member 2 and the rest of the team. Mention any agreed changes to the file contract.]`

## Tools and AI assistance

- Languages / libraries / tools used: `[List only those actually used.]`
- AI assistance: `[State whether AI tools were used, what they helped with, and what you personally reviewed, tested, corrected or validated. If none, say none.]`
- External material: `[List any documentation or sources used, if applicable.]`

## Limitations and follow-up

`[Record unresolved dataset issues, checks not performed, assumptions, and any work left to another member. If no known limitation remains, say so and explain the scope of the checks.]`

## Contributor confirmation

I confirm that this record describes my own contribution accurately, distinguishes my work from the work of other members and AI tools, and is consistent with the cited branch changes and evidence.

**Name:** `[Full name]`  
**Date:** `[Date]`
