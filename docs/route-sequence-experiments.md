# Training-only route sequence investigation

## Scope and reproducibility

The baseline is the frozen Decision Tree configuration (depth 9, minimum leaf size 125, seed 42) and decoder settings from `artifacts/pathsnap.joblib`. Its SHA-256 is `ba5b06b8b764be2e97fa5b64339460676235512fb836df525590c457a2d34404`. This investigation uses only 80 training trips, in the three original trip-disjoint GroupKFold assignments. Each fold fits its own tree on the original stride-2 candidate training rows and predicts every held-out observation. Held-out reference files are opened after that trip has been decoded for the comparisons. The previously reported official evaluation is historical and was neither reopened nor rerun.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m evaluation.sequence_experiments --data "../Student folder"
```

The ignored `artifacts/experiments/sequence_improvements/` directory stores frozen input hashes, the model settings, dependency versions, folds, fit seed, OOF baseline, trial definitions, results, and independent fold models and hashes. Runtime covers candidate generation, model scoring and decoding. It excludes disk I/O, training, reference alignment and diagnostic tracing. Trial variants reuse already computed candidates and charges each variant the measured candidate/scoring time for its shortlist.

## Metric audit

- Top-1 is the fraction of aligned observations whose selected directed arc equals the alignment label. Candidate miss counts an aligned observation whenever its reference arc is absent from the shortlist.
- Candidate macro F1 is binary candidate F1 at threshold 0.5 averaged over positive and negative classes. It is a separate metric from observation-level arc ranking. Direct continuity uses consecutive observations with predictions at both ends and credits equal arcs or a shared directed endpoint. It neither requires the entire reference route to be visited nor verifies a bridge between the two states.
- Sequence F1 is twice the longest common subsequence length divided by predicted plus reference sequence length. The prediction is the flattened reconstructed legs, including inserted bridges, and the reference is the ordered arc file. Both collapse adjacent equal directed arc IDs after dropping invalid sentinels. Consecutive duplicates can collapse across a restart boundary. Nonconsecutive repeats are retained, and reverse arcs retain separate identities. This is the existing ordered route measure. The guidelines call for sequence-level performance and do not prescribe a separate leg-aware formula.
- The bit-parallel LCS implementation matched a scalar dynamic program on 961 synthetic sequence pairs including empty sequences and repeated arcs. Synthetic tests also checked intermediate bridge order, missing candidates, reverse-direction disconnection, invalid timestamps, and gap resets. The existing metric definitions were preserved.
- The historical decoder report uses equal-weight trip means. This experiment reports those and observation-weighted Top-1 and candidate miss over aligned observations. Per-trip diagnostics distinguish ordered LCS omissions and insertions from literal unique arc absence.

## How the decoder can miss sequence arcs

The emission weight is clipped log tree probability plus a Gaussian GPS-distance penalty. The transition weight penalizes the mismatch between GPS displacement and the sum of previous-arc remainder, directed shortest bridge, and next-arc progress. Same-arc backward movement has a separate jitter allowance. A segment pair can be blocked by bounded network reachability or by distance given elapsed time. If the finite restart hypothesis wins, the decoder starts a new leg and inserts no bridge across that seam. Large gaps and invalid time also reset the chain. Shortest paths provide a plausible connection between states and may differ from the reference's intervening arc sequence.

The baseline trace counts candidate-pair targets unreachable within the router's distance bound as disconnected transitions. This count includes pairs that Viterbi never selects and is not a count of graph components. The trace separately records steps where every plausible pair was blocked, selected transition restarts, gap/time resets, and intermediate arcs actually inserted. Traced and untraced predictions are checked for exact equivalence for every trip.

Candidates come from the 64 nearest midpoint samples, spaced up to 35 m apart. The system deduplicates directed arc IDs, ranks these by exact projected point-to-segment distance, and keeps eight candidates. The shortlist-size trial changes only the inference shortlist. The trees still fit baseline-width candidates, so it measures the effect of exposing the frozen fold tree to lower-ranked arcs.

## Out-of-fold baseline and worst training trips

Across all 80 trips, mean Sequence F1 was 86.68%, median Sequence F1 was 91.56%, mean trip Top-1 was 88.09%, and observation-weighted Top-1 was 88.31%. Mean candidate macro F1 was 87.33%, direct continuity was 96.51%, and candidate miss was 1.56% by trip or 1.37% when weighted by aligned observations. Baseline mean candidate-through-decoder time was 0.397 seconds per trip.

| Held-out training trip | Fold | Top-1 | Direct continuity | Sequence F1 | Candidate miss | Reference length | Predicted length | LCS | Insertions from LCS | Restarts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 00000072 | 0 | 74.30% | 80.99% | 24.79% | 15.79% | 131 | 926 | 131 | 795 | 0 |
| 00000033 | 2 | 39.69% | 99.08% | 26.32% | 31.11% | 169 | 1,062 | 162 | 900 | 21 |
| 00000002 | 0 | 78.61% | 97.13% | 27.56% | 0.98% | 262 | 1,639 | 262 | 1,377 | 25 |
| 00000054 | 2 | 61.97% | 98.19% | 45.64% | 25.81% | 422 | 1,366 | 408 | 958 | 184 |
| 00000061 | 0 | 64.24% | 88.59% | 52.34% | 10.38% | 296 | 774 | 280 | 494 | 11 |
| 00000070 | 2 | 90.75% | 98.07% | 68.40% | 0.92% | 149 | 275 | 145 | 130 | 1 |

Sequence lengths are collapsed lengths. Across 80 trips, the ordered alignment counted 9,503 predicted insertions versus 673 omissions. Exact recovery of the reference subsequence on trips 00000072 and 00000002 shows how excess arcs can dominate the denominator. The former inserted 588 bridge arcs with one continuous leg. The latter inserted 207 bridge arcs and restarted 25 times, so bridge insertion alone cannot account for the 1,377 excess arcs. Trip 00000070 shows a high-Top-1 case with 130 excess arcs and just one restart. Candidate misses were concentrated in some difficult trips. They were below 1% on trips 00000002 and 00000070, so a wider shortlist alone cannot explain these errors. Only 2,522 of 19,313 GPS observations in trip 00000054 obtained alignment labels, which limits interpretation of its observation-level metrics.

Across the baseline there were 844 leg restarts, of which 711 followed scored transition decisions and 133 followed time gaps. At 69 steps the entire candidate-pair matrix had no plausible transition. Thus hard disconnection and long gaps explain some fragmentation, while the decoder also chooses a soft restart at many steps with at least one feasible pair. No training observations were unmatched.

## Reciprocal-arc follow-up

The follow-up subtracts a soft log-score penalty when switching directly between two candidate arcs whose endpoints are reversed. A legal U-turn remains possible. The alternative router stays in the experiment module. It reuses the baseline fold weights, shortlist, emissions, decoder configuration and bridge reconstruction. Standalone rerun after the baseline:

```powershell
python -m evaluation.reciprocal_experiments --data "../Student folder"
```

The follow-up reproduced each trip's baseline Sequence F1 before scoring the variants. Its evidence is in `reciprocal.json`. Across baseline route legs there were 5,162 immediate reciprocal hops. Penalty 3 reduced this to 1,798 and reduced sequence insertions from 9,503 to 6,383, with omissions moving from 673 to 674. On trip 00000033, reciprocal hops fell from 839 to 11 and Sequence F1 rose from 26.32% to 80.00%. On trip 00000002, reciprocal hops fell from 1,055 to 318 and Sequence F1 rose from 27.56% to 41.23%. Trip 00000072 improved only from 24.79% to 25.44%, so broader bridge cycling and candidate recall remain limitations.

The three fold trees used relative candidate distance (56.74% of mean fitted impurity importance) and heading agreement (30.77%) most heavily. Speed, segment length, projected fraction and directed degree had substantially smaller impurity shares. These training-fit summaries are descriptive. No feature changes or classifier replacement were tested, since the decoder follow-up improved performance using the same fitted trees. Directed bridging was verified with synthetic cases and kept intact.

## Controlled comparison

All percentages are means across the same 80 held-out training trips. Time is mean seconds per trip from candidate generation through decoding. The runs overlapped for part of the measurement, so the timings are descriptive.

| Experiment | Sequence F1 | Top-1 | Continuity | Candidate miss | Seconds | Trips improved / worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline (sigma 35 m, beta 15 m, restart 10, reach 450 m, gap 30 s, 8 candidates) | 86.68% | 88.09% | 96.51% | 1.56% | 0.397 | - |
| GPS sigma 22 m | 86.63% | 88.07% | 96.50% | 1.56% | 0.388 | 6 / 17 |
| GPS sigma 55 m | 86.70% | 88.12% | 96.51% | 1.56% | 0.387 | 7 / 5 |
| Transition beta 8 m | 88.47% | 88.50% | 96.70% | 1.56% | 0.392 | 68 / 4 |
| Transition beta 30 m | 83.71% | 87.57% | 96.08% | 1.56% | 0.388 | 1 / 76 |
| Restart cost 5 | 85.52% | 87.45% | 96.30% | 1.56% | 0.392 | 8 / 61 |
| Restart cost 18 | 87.00% | 88.68% | 96.55% | 1.56% | 0.392 | 33 / 11 |
| Network reach 650 m | 86.69% | 88.09% | 96.51% | 1.56% | 0.443 | 2 / 0 |
| Gap limit 60 s | 86.73% | 88.11% | 96.51% | 1.56% | 0.391 | 9 / 2 |
| Shortlist 12 | 87.35% | 88.23% | 96.68% | 1.07% | 0.568 | 42 / 1 |
| Reciprocal penalty 3 | 89.59% | 88.92% | 96.33% | 1.56% | 0.442 | 65 / 1 |
| Reciprocal penalty 8 | 89.60% | 88.97% | 96.31% | 1.56% | 0.431 | 65 / 2 |

Tightening transition beta to 8 m improved all three folds and raised continuity. Widening the shortlist to 12 improved candidate recall and Sequence F1, with roughly 43% higher observed runtime. It did less for sequence quality than penalising reciprocal switches. Changing GPS emission scale had little effect. A larger time-gap limit likewise had little effect, and changing it left temporal feature generation unchanged. Increasing network reach affected only two trips, consistent with the elapsed-time distance cap limiting shorter intervals. Parameter ranges were predeclared for the first sweep, with the reciprocal trials as a separately recorded follow-up.

## Recommended development candidate

Keep the existing tree and baseline decoder settings, and test a soft reciprocal-switch penalty of **3** in the experimental router. This improved Sequence F1 from 86.68% to 89.59% (+2.91 percentage points), mean trip Top-1 from 88.09% to 88.92%, and observation-weighted Top-1 from 88.31% to 89.28%. Candidate miss was unchanged. Direct continuity declined 0.17 points and mean inference time was 0.442 s vs 0.397 s in the baseline measurement.

The sequence gain was positive in all three folds (+2.88, +1.43 and +4.48 points). Of 80 trips, 65 improved, one declined by 0.22 points, and 14 tied. Removing the largest-gain trip still leaves a mean improvement of 2.27 points across the other 79. Penalty 8 improved mean Sequence F1 by a further 0.004 percentage points and regressed on two trips. The milder penalty offers nearly the same sequence gain while preserving more flexibility for genuine reversals. Beta 8 m is a separate option if improving direct continuity is a requirement. No combined modifications were tested.

The same grouped folds guided trial selection, so the observed gain is development evidence. Keep production unchanged pending team approval. Once a candidate is explicitly frozen, follow the team's one-run official evaluation policy.

## Changed files and checks

- `evaluation/sequence_experiments.py` runs the grouped baseline and the parameter and shortlist sweep.
- `evaluation/reciprocal_experiments.py` runs the soft reciprocal-edge experiments on the saved fold models.
- `route_reconstruction/decoder.py` adds opt-in diagnostic counts. Tracing was checked for identical predictions to the ordinary decoder on all 80 trips.
- `tests/test_pipeline.py` adds four synthetic tests to the four existing tests. All eight passed.
- `.gitignore` keeps scratch fold artifacts and diagnostics outside tracked deliverables.
- `docs/route-sequence-experiments.md` records methods, measured results and limitations.

The production bundle and historical result hashes were verified unchanged. The official data and student-test partition were not used for the new experiments.
