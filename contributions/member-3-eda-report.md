# Individual Contribution Record — Member 3: Exploratory Analysis, Visualisation and Technical Report

> **Complete the placeholders and remove any statement that does not match the work you personally performed.** This record describes the agreed Member 3 workstream; it must be checked against the actual branch diff before submission.

## Contributor details

| Field | Entry |
|---|---|
| Contributor | `[Full name]` |
| GitHub username | `[GitHub username]` |
| Student ID / SRN | `[Include only if required by the course or event]` |
| Assigned branch | `feat/member-3-analysis-report` |
| Contribution period | `[Start date – end date]` |
| Pull request | `[PR URL]` |
| Main contribution commits | `[Commit hashes / links]` |

## Contribution summary

Member 3's allocated responsibility was to analyse the prepared PathSnap data and communicate the system's design, findings and limitations through reproducible exploratory analysis, map-based visualisations and the technical report.

This workstream is responsible for presenting what the data and experiments show. It should not imply that the team collected the original GPS trajectories: the source dataset was supplied by the organisers.

## Work personally performed

| Work area | What I personally did | Evidence / files |
|---|---|---|
| Exploratory data analysis | `[Describe the questions, statistics and comparisons you personally examined.]` | `[Exact path / commit]` |
| GPS / road visualisation | `[Describe maps, trajectory plots, layers, legends and the inputs used.]` | `[Exact path / commit]` |
| Model / decoder result presentation | `[Describe which existing experiment outputs you processed or visualised. Identify who ran the experiments.]` | `[Exact path / commit]` |
| Technical report | `[Describe sections you drafted, figures/tables you produced and technical explanations you verified.]` | `[Exact path / commit]` |
| Requirements / evidence tracking | `[Describe checklist maintenance and evidence linking, if performed.]` | `[Exact path / commit]` |

## Files owned or materially changed

The agreed branch allocation identified these likely files. Keep only files that appear in your actual contribution and describe your changes precisely.

| File | Role in the workstream | My actual change |
|---|---|---|
| `data_processing/explore.py` | Exploratory analysis | `[Describe the analyses, calculations or outputs you implemented.]` |
| `visualizations/maps.py` | Map / trajectory visualisation | `[Describe the map layers, geometry handling and output you implemented.]` |
| `results/exploration.csv` | Tabular EDA results | `[Describe how it was generated and checked.]` |
| `results/exploration.json` | Structured EDA results | `[Describe how it was generated and checked.]` |
| `results/gps_counts.png` | GPS data-count visualisation | `[Describe the plot and its source data.]` |
| `results/student_trajectory.png` | Student trajectory visualisation | `[Describe the trip and what the visualisation demonstrates.]` |
| `results/student_eda_map.html` | Interactive EDA map | `[Describe its layers and how it was generated.]` |
| `reporting/build.py` | Technical-report generation | `[Describe the report-generation changes you made.]` |
| `TECHNICAL.md` | Technical explanation and results | `[Identify the sections you personally authored or revised.]` |
| `REQUIREMENTS_CHECKLIST.md` | Requirement and evidence status | `[Describe which items you checked and what evidence supports them.]` |
| `PathSnap-Technical-Report.pdf` | Generated report artifact | `[Confirm whether you generated/reviewed it; identify source inputs.]` |
| Other: `[path]` | `[Purpose]` | `[Actual change]` |

## Technical and analytical approach

Explain your own work in enough detail for a reviewer to reproduce and question it. Address the relevant items below:

1. Which dataset partitions and prepared outputs were used for EDA, and how you avoided mixing development and official-evaluator results.
2. Which distributions, counts, gaps, anomalies or alignment patterns you examined.
3. How GPS points and road geometry were projected or displayed on maps, including how visual layers were distinguished.
4. How figures and tables were generated from code or saved experiment outputs rather than manually fabricated.
5. How model and decoder metrics were described, including the distinction between observation-level and sequence-level evaluation.
6. How report statements were checked against actual implementation, logs and experiment outputs.

**My analysis / report explanation:**

`[Write your explanation here. Include actual analysis questions, methods, interpretations, and known limitations.]`

## Results and evidence

| Deliverable / check | Command / method | Actual result | Evidence |
|---|---|---|---|
| EDA generation | `[Command]` | `[Observed result]` | `[Output / commit]` |
| Figure generation | `[Command]` | `[Figures generated and checked]` | `[Image / commit]` |
| Map generation | `[Command]` | `[Map generated and checked in browser]` | `[HTML / screenshot]` |
| Report build | `[Command]` | `[Build result, page count if verified]` | `[PDF / commit]` |
| Technical accuracy review | `[Method]` | `[Claims / sections verified and by whom]` | `[Review record]` |

When reporting scores, always name the evaluation split and metric definition. In particular, the 89.59% Sequence F1 result from the reciprocal-penalty experiment is a grouped development-validation result on 80 held-out training trips; the previously reported 86.48% is mean Sequence F1 on the ten official evaluator trips. They must not be presented as a direct before/after comparison on the same test set.

## Collaboration and handoff

`[Explain what analysis, figures, report sections or evidence you delivered to the other members, and which raw results or implementation details they supplied.]`

## Tools and AI assistance

- Languages / libraries / tools used: `[List only those actually used.]`
- AI assistance: `[State whether AI tools helped with code, analysis, editing or report drafting. Identify what you personally checked, reproduced, corrected and can explain. Do not claim AI-generated work as unaided personal work.]`
- External material: `[List sources used for definitions, methods or background, if applicable.]`

## Limitations and follow-up

`[Record missing evidence, plots not independently verified, limitations of the dataset or analyses, and report items still awaiting final deployment or evaluator confirmation.]`

## Contributor confirmation

I confirm that this record describes my own contribution accurately, distinguishes my work from the work of other members and AI tools, and is consistent with the cited branch changes and evidence.

**Name:** `[Full name]`  
**Date:** `[Date]`
