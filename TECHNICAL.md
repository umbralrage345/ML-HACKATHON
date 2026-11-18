# Technical notes

## Data and alignment

The supplied development dataset contains 80 training trips and 10 student-test trips. The expanded inventory records file sizes, GPS and reference row counts, coordinate bounds, timestamp gaps, weak road-network components, isolated nodes and directed reference discontinuities. It found 13 training reference breaks and one student-test reference break. The largest timestamp gap was 153,064 seconds in training and 210 seconds in student testing.

Coordinates are projected to local east/north metres using an equirectangular tangent approximation centred on each road network. Spatial candidate generation queries the nearest 64 segment midpoint samples spaced at most 35 m apart, deduplicates arc IDs, then ranks up to eight arcs by exact projected point-to-segment distance within that shortlist. The candidate set can miss the reference arc in dense road geometry. Features use distance, endpoints, projection fraction, length, heading agreement, sampling interval, speed, rank, relative distance, and directed node degrees. Heading and speed reset at missing rows, nonpositive intervals, and gaps above 30 seconds.

The raw route lists ordered arc occurrences. A monotone dynamic program aligns GPS rows to those occurrences by minimizing capped distance to their geometry subject to weak penalties for advances and skipping route endpoints. It permits repeated observations on the same occurrence and permits traversed arcs without GPS observations. Observations farther than 75 m from the assigned arc are left unlabelled. The synthetic tests check direction, skipped arcs, and invalid rows. The real-data [alignment diagnostics](results/alignment.json) track coverage, distance residuals, and candidate misses. The student-test median residual was 5.28 m and 19,139 of 19,160 observations were aligned. Training alignment covered 187,013 of 208,417 observations, with a 5.70 m median and 142.08 m 95th-percentile residual. These labels are geometry-derived estimates. Parallel roads, junctions, and large dropouts can make the exact observation-level arc ambiguous.

## Classifiers and metrics

All five classifiers emit candidate probabilities and use the same candidate rows and grouped validation assignments. Logistic regression provides a scaled linear baseline. Gaussian naive Bayes measures how far low-cost independent feature likelihoods can go despite correlated distance features. The decision tree tests nonlinear thresholds and feature interactions, Extra Trees averages randomized trees, and histogram gradient boosting tests a sequential additive ensemble with bounded per-tree complexity. The implementation uses the classifiers' default supervised losses or splitting criteria and explicitly records constructor settings. Student-test top-1 selects the initial model, with grouped CV macro F1 breaking ties. The Bayesian TPE objective is mean validation-fold candidate macro F1. The tuned and original candidates are compared by the same student-test ordering for deployment.

Candidate metrics compare binary candidate correctness using a probability threshold of 0.5. Candidate misses are included in the aligned observation top-1 denominator, even though all candidate targets for that row are negative. Observation top-1 evaluates alignment-derived targets. Candidate miss rate gives the fraction of aligned observations whose reference arc was absent from the shortlist. Direct continuity is the fraction of adjacent predicted observations with identical arcs or a shared directed endpoint. Sequence F1 is twice the longest common subsequence length divided by the sum of compared lengths after consecutive duplicate collapse. It measures ordered agreement with the full supplied reference sequence. The decoder comparison averages per-trip measures. The initial model comparison weights top-1 and miss rates by aligned observation count.

## Route decoding and serving

Hidden states are the candidate arc IDs with each observation's projected fraction. Emissions combine the log classifier score and a Gaussian GPS-distance term. The Viterbi recurrence adds each current state's emission to the maximum previous-state score plus its transition weight. A directed shortest-path bridge gives the network distance between projected positions. The transition penalizes deviations from GPS displacement and limits the distance by elapsed seconds. A finite restart cost allows a new route leg when every plausible connection fails or a disconnected alternative scores better. Invalid observations, nonpositive timestamps, and long gaps restart decoding. An invalid or unmatched row returns a null arc in the API. Selected connected bridges contribute their intermediate arcs to the reconstructed route legs. Student-test sequence F1 selects the decoder settings across the documented grid.

The inference entry point loads GPS and road geometry only. The evaluator loads the private reference after inference and returns numeric aggregates. The official final data is expected on laptop 1; all development runs use only the two supplied development splits. The maps in the results directory show student-test reference routes for development review. Maps delivered by the API contain GPS, nearby roads, and the predictions.

## Measured development results

The table shows candidate macro F1 across grouped validation folds and the micro-average aligned observation top-1 across the student-test trips. The candidate log loss uses the same student-test candidates.

| Model | Grouped CV macro F1 | Student top-1 | Student candidate macro F1 | Student log loss |
| --- | ---: | ---: | ---: | ---: |
| Logistic regression | 0.8651 | 0.7940 | 0.8752 | 0.1489 |
| Gaussian naive Bayes | 0.7365 | 0.7591 | 0.7276 | 0.8102 |
| Decision tree | 0.8695 | 0.7986 | 0.8794 | 0.1433 |
| Extra Trees | 0.8659 | 0.7894 | 0.8769 | 0.1422 |
| Histogram gradient boosting | 0.8743 | 0.7965 | 0.8832 | 0.1298 |
| Tuned decision tree | 0.8708 | 0.8012 | 0.8822 | 0.1275 |

The decision tree led the five untuned models on student-test top-1. Eight TPE trials selected a tree with depth 9 and a minimum of 125 samples per leaf. The tuned classifier scored all ten student-test candidate sets in approximately 0.022 seconds in this run, excluding I/O, feature extraction and decoding. Per-trip results, confusion matrices, timings, fold assignments and full trial records are in [models.json](results/models.json), [protocol.json](results/protocol.json) and [bayesian.json](results/bayesian.json).

| Tuned classifier on student-test trips | Mean trip top-1 | Mean direct continuity | Mean sequence F1 |
| --- | ---: | ---: | ---: |
| Independent predictions | 0.8090 | 0.8912 | 0.5891 |
| Viterbi reconstruction | 0.8847 | 0.9711 | 0.8954 |

The best decoder configuration used a 15 m transition residual scale, 35 m GPS emission scale, and restart penalty of 10. The [decoder comparison](results/decoder.json) retains each tested configuration and its per-trip results. The [student-test prediction map](results/student_prediction_map.html) overlays the selected decoder's output on GPS, roads and the private development reference. Feature permutation sensitivity on the student-test split is recorded in [feature_sensitivity.json](results/feature_sensitivity.json). Permuting correlated candidate features is a diagnostic of model sensitivity and can create combinations rarely seen in the input data.

Heading agreement and distance above the best candidate produced the largest measured decreases in candidate macro F1 when permuted (0.193 and 0.138 respectively). The browser smoke test used separate local HTTP ports for FastAPI and the UI. It listed all ten student-test trips and displayed a Folium prediction and aggregate metrics for trip 00000000.
