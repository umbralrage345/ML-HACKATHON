# Individual Contribution Record — Member 2: Preprocessing and Feature Preparation

> **Complete the placeholders and remove any statement that does not match the work you personally performed.** This record describes the agreed Member 2 workstream; it must be checked against the actual branch diff before submission.

## Contributor details

| Field | Entry |
|---|---|
| Contributor | `[Full name]` |
| GitHub username | `[GitHub username]` |
| Student ID / SRN | `[Include only if required by the course or event]` |
| Assigned branch | `feat/member-2-preprocessing` |
| Contribution period | `[Start date – end date]` |
| Pull request | `[PR URL]` |
| Main contribution commits | `[Commit hashes / links]` |

## Contribution summary

Member 2's allocated responsibility was to transform the raw GPS observations and directed road network into a consistent, model-ready representation. This workstream connects the organiser-supplied trip files to candidate road segments, per-observation features, reference alignment and prepared training data.

The intended handoff is a repeatable preprocessing pipeline that preserves observation identity and produces aligned candidate/features/label arrays for downstream model training and sequence decoding.

## Work personally performed

Complete the table with concrete implementation details and the files where the work can be inspected.

| Work area | What I personally did | Evidence / files |
|---|---|---|
| Raw trip loading | `[Describe parsing, validation and error handling that you implemented.]` | `[Exact path / commit]` |
| Coordinate projection | `[Describe the projection and coordinate handling actually implemented.]` | `[Exact path / commit]` |
| Candidate generation | `[Describe spatial search, shortlist, projection-to-segment distance, deduplication and candidate limits actually used.]` | `[Exact path / commit]` |
| Feature engineering | `[List the features you implemented and how missing/invalid values were handled.]` | `[Exact path / commit]` |
| Reference alignment | `[Describe how reference route occurrences were aligned to observations, if this was your work.]` | `[Exact path / commit]` |
| Prepared data output | `[Describe array fields, file format and consistency checks.]` | `[Exact path / commit]` |

## Files owned or materially changed

The agreed branch allocation identified these likely files. Keep only files that appear in your actual contribution and describe your changes precisely.

| File | Role in the workstream | My actual change |
|---|---|---|
| `data_processing/trips.py` | Raw trip loading and validation | `[Describe the functions or logic you implemented or changed.]` |
| `features/candidates.py` | Road candidate generation and observation features | `[Describe the functions or logic you implemented or changed.]` |
| `evaluation/reference.py` | Reference route alignment / label preparation | `[Describe your actual contribution; do not claim evaluation work you did not perform.]` |
| `training/prepare.py` | Prepared training-data generation | `[Describe the functions or logic you implemented or changed.]` |
| `docs/prepared-data.md` | Prepared-data format and contract documentation | `[Confirm whether this file exists and describe your contribution.]` |
| Other: `[path]` | `[Purpose]` | `[Actual change]` |

## Technical approach

Explain the actual implementation. The following project-specific design details may be relevant; retain them only if your branch implements them:

- GPS and road coordinates are represented in a local metric coordinate system for distance calculations.
- Road candidates are generated from nearby road geometry and then ranked using point-to-segment distance.
- Candidate features may include distance to segment, endpoint distances, projection fraction, segment length, heading agreement, sampling interval, speed, candidate rank and road-network degree information.
- Heading and speed calculations need careful handling around missing records, invalid intervals and long time gaps.
- Reference alignment must respect the ordered route while allowing observations to map to route occurrences and allowing route arcs with no directly aligned GPS observation.
- Prepared trip records may include features, labels, original observation IDs, residuals, projection fractions, candidate arc IDs and reference route data.

**My implementation explanation:**

`[Explain the code path, key algorithms, data structures, parameter choices, edge cases and trade-offs you personally implemented.]`

## Verification and results

| Check | Command / method | Actual result | Evidence |
|---|---|---|---|
| Loader validation | `[Command]` | `[Pass / fail and summary]` | `[Test/log]` |
| Candidate generation | `[Command]` | `[Observed result, including candidate counts or miss analysis if measured]` | `[Output]` |
| Feature validity | `[Command]` | `[Observed result]` | `[Test/log]` |
| Reference alignment | `[Command]` | `[Observed result and limitations]` | `[Test/log]` |
| Prepared-data consistency | `[Command]` | `[Array shapes, IDs, labels or other checks actually run]` | `[Test/log]` |

Only report metrics or checks that you personally executed or independently verified. Distinguish training, student-test and official-evaluator data; do not use evaluation labels to influence inference-time preprocessing.

## Collaboration and handoff

`[Explain the interface handed to Member 3 and Member 4: expected input/output formats, array shapes, IDs, assumptions, parameter configuration and known limitations.]`

## Tools and AI assistance

- Languages / libraries / tools used: `[List only those actually used.]`
- AI assistance: `[State whether AI tools were used, what they helped with, and what you personally reviewed, tested, corrected or validated. If none, say none.]`
- External material: `[List any documentation or sources used, if applicable.]`

## Limitations and follow-up

`[Record unresolved edge cases, candidate misses, projection assumptions, long-gap handling, alignment limitations and follow-up work. Include only issues relevant to your implementation.]`

## Contributor confirmation

I confirm that this record describes my own contribution accurately, distinguishes my work from the work of other members and AI tools, and is consistent with the cited branch changes and evidence.

**Name:** `[Full name]`  
**Date:** `[Date]`
