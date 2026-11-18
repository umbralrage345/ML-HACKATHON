"""Generate the consolidated PathSnap PDF from recorded development outputs."""
import argparse
import csv
from html import escape
import json
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DETAILS = {
    "logistic": ("Logistic regression", "Linear probabilistic",
        "A scaled linear baseline tests whether distance and heading are sufficient as additive effects. It is fast and transparent, but a single linear boundary cannot express interactions around junctions.",
        "L2-regularized binary log loss."),
    "naive_bayes": ("Gaussian naive Bayes", "Generative probabilistic",
        "A cheap probability baseline tests separation under Gaussian feature likelihoods. Distance, rank and endpoint distances are correlated, so the independence assumption can produce overconfident probabilities.",
        "Class-conditional Gaussian maximum likelihood with variance smoothing and empirical class priors."),
    "decision_tree": ("Decision tree", "CART",
        "A single tree can combine heading and distance thresholds and is straightforward to inspect. Leaf frequency estimates are sensitive to the chosen splits and minimum leaf count.",
        "Greedy Gini impurity reduction. Probabilities are class fractions in terminal leaves."),
    "extra_trees": ("Extra Trees", "Randomized ensemble",
        "Averaging randomized trees permits nonlinear interactions and can stabilize individual splits. Inference computes 28 tree outputs and randomized splits can lose useful thresholds.",
        "Randomly proposed splits selected by Gini impurity reduction. Predictions average tree leaf probabilities."),
    "hist_gradient": ("Histogram gradient boosting", "Boosted trees",
        "Sequential trees can correct difficult candidate errors and model feature interactions; histograms keep fitting practical. Bin quantization, serial boosting and complexity can affect accuracy and latency.",
        "Additive gradient boosting on binary log loss with histogram-binned features."),
    "tuned": ("Tuned decision tree", "CART",
        "This is a second configuration of the CART family. A shallower tree and larger leaves constrain complexity and pool more observations for leaf probabilities.",
        "Same CART fitting objective as the original tree; Optuna selects settings by grouped validation macro F1."),
}


def load(directory, name):
    return json.loads((directory / (name + ".json")).read_text(encoding="utf-8"))


def plots(directory, models, gaps):
    labels = [DETAILS[key][0] for key in models]
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    definitions = [
        ("Training grouped CV macro F1", lambda record: record["cv_macro_f1"], 1),
        ("Student-test aligned top-1", lambda record: record["student"]["top1"], 1),
        ("Student-test candidate macro F1", lambda record: record["student"]["macro_f1"], 1),
        ("Student-test binary log loss (lower is better)", lambda record: record["student"]["log_loss"], None),
    ]
    for axis, (title, metric, maximum) in zip(axes.flat, definitions):
        values = [metric(record) for record in models.values()]
        bars = axis.barh(labels, values, color=["#356477"] * 5 + ["#008578"])
        axis.invert_yaxis()
        axis.set(title=title, xlim=(0, maximum or max(values) * 1.20))
        axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
        axis.tick_params(axis="y", labelsize=8)
    fig.savefig(directory / "report_comparisons.png", dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(10, 6), layout="constrained")
    for axis, label, model in zip(axes.flat, labels, models.values()):
        counts = model["student"]["confusion_matrix"]
        relative = [[n / max(1, sum(row)) for n in row] for row in counts]
        axis.imshow(relative, cmap="Blues", vmin=0, vmax=1)
        for i, row in enumerate(counts):
            for j, count in enumerate(row):
                axis.text(j, i, f"{count:,}", ha="center", va="center",
                          color="white" if relative[i][j] > .55 else "#172433")
        axis.set(xticks=[0, 1], yticks=[0, 1], xticklabels=["Negative", "Positive"],
                 yticklabels=["Negative", "Positive"], title=label, xlabel="Predicted", ylabel="Actual")
    fig.savefig(directory / "report_confusion.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 3), layout="constrained")
    x = list(range(len(labels)))
    for subset, key, marker in (("Fit", "fit_macro_f1", "o"), ("Held-out trips", "validation_macro_f1", "s")):
        axis.plot(x, [mean(fold[key] for fold in gaps[name]) for name in models], marker,
                  label=subset)
    axis.set(xticks=x, xticklabels=labels, ylabel="Macro F1", ylim=(.65, .95))
    axis.tick_params(axis="x", rotation=16, labelsize=8)
    axis.legend()
    fig.savefig(directory / "report_generalization.png", dpi=160)
    plt.close(fig)


def build(directory, destination):
    models = load(directory, "models")
    gaps = load(directory, "generalization")
    protocol = load(directory, "protocol")
    search = load(directory, "bayesian")
    decoder = load(directory, "decoder")
    trial = next(r for r in decoder["decoder_trials"] if r["config"] == decoder["selected"])
    baseline = decoder["classifier"]
    alignment = load(directory, "alignment")
    http = load(directory, "development_http")
    with (directory / "exploration.csv").open(encoding="utf-8") as file:
        inventory = list(csv.DictReader(file))
    plots(directory, models, gaps)
    styles = getSampleStyleSheet()
    for name, size, leading in [("BodyText", 9, 13), ("Heading1", 18, 22), ("Heading2", 12, 16)]:
        styles[name].fontSize, styles[name].leading = size, leading
    styles["Normal"].alignment = TA_LEFT
    story = []

    def paragraph(text, style="BodyText"):
        story.append(Paragraph(escape(text), styles[style]))

    def section(number, name):
        if story:
            story.append(PageBreak())
        paragraph(f"{number}. {name}", "Heading1")

    def figure(name, caption, limit=465, height=355):
        picture = Image(str(directory / name))
        ratio = min(limit / picture.imageWidth, height / picture.imageHeight)
        picture.drawWidth, picture.drawHeight = picture.imageWidth * ratio, picture.imageHeight * ratio
        story.extend([Spacer(1, 8), picture])
        paragraph(caption)

    def table(headers, rows, widths=None):
        widths = widths or [470 / len(headers)] * len(headers)
        values = [[Paragraph(escape(str(value)), styles["BodyText"]) for value in line]
                  for line in (headers, *rows)]
        matrix = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
        matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8e5e9")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7f8")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([Spacer(1, 8), matrix, Spacer(1, 8)])

    section(1, "Dataset Understanding and Exploratory Data Analysis")
    paragraph("PathSnap | Consolidated technical report", "Heading2")
    paragraph("This report presents recorded development results from 80 training and 10 student-test trips. Official evaluator scores and two-laptop demonstration evidence are pending.")
    paragraph(f"Histogram gradient boosting had the highest student-test candidate macro F1 "
              f"({models['hist_gradient']['student']['macro_f1']:.2%}). The tuned decision tree had the highest "
              f"pooled observation top-1 ({models['tuned']['student']['top1']:.2%}) and was selected for deployment. "
              f"Adding Viterbi increased mean route sequence F1 from {baseline['mean_by_trip']['sequence_f1']:.2%} "
              f"to {trial['mean_by_trip']['sequence_f1']:.2%} across the ten student-test trips.")
    columns = ["Partition", "Trips", "GPS rows", "Invalid GPS", "Gaps >30 s", "Reference breaks"]
    rows = []
    for split, quality in alignment.items():
        selected = [r for r in inventory if r["partition"] == split]
        rows.append([split, len(selected), f'{quality["observations"]:,}',
                     sum(int(r["invalid_gps_rows"]) for r in selected),
                     sum(int(r["steps_over_30_seconds"]) for r in selected),
                     sum(int(r["reference_breaks"]) for r in selected)])
        paragraph(f"{split}: {quality['aligned']:,} observations aligned; median geometry residual "
                  f"{quality['median_alignment_error_m']:.2f} m; observed maximum gap "
                  f"{max(float(r['max_gap_seconds']) for r in selected):,.0f} s. "
                  f"Mean isolated valid nodes per trip {mean(int(r['isolated_nodes']) for r in selected):.1f}. "
                  f"Candidate misses: {quality['missing_candidates']:,} among aligned observations.")
    table(columns, rows, [90, 45, 80, 70, 80, 95])
    paragraph("Each supplied trip has a track, nodes, directed arcs and an ordered arc-ID reference. Parsers preserve row IDs, validate coordinates and timestamps, and test node bounds. Missing file sizes and invalid rows are counted separately. A local projection converts angular coordinates to metres. The candidate shortlist uses the nearest 64 midpoint samples spaced at most 35 m apart and ranks up to eight distinct arcs by segment distance. Dense junctions, parallel roads, GPS error and shortlist truncation can hide the reference arc.")
    paragraph("GPS locations can be offset by noise, and irregular sampling drops information between observations. A monotone geometry alignment allows repeated observations on an arc and skipped arcs. It uses capped residuals and weak progress and endpoint penalties. Residuals over 75 m are unlabelled. The reference encodes chronological arc occurrences and contains directed breaks. It provides approximate observation targets after alignment, with ambiguity at junctions, GPS gaps and competing parallel arcs.")
    paragraph("Features combine segment and endpoint distances, projected fraction, length, heading agreement, interval, speed, rank, relative distance and directed degrees. Heading and relative distance had the largest held-out permutation effects. Temporal motion features reset at invalid rows, nonpositive intervals and gaps above 30 s.")
    figure("gps_counts.png", "GPS row counts by development partition. Source: exploration.csv.", height=90)
    figure("student_trajectory.png", "Student-test trip 00000000. Projected GPS and nearby road segments.", height=105)

    section(2, "Model Experimentation and Comparison")
    paragraph(f"Every fitting trip is sampled at stride {protocol['fit_stride']}. All validation observations are scored. Three GroupKFold splits keep each trip intact, and scaling is fitted inside models that use it. Student testing is held out of fitting and TPE. The comparison uses observation top-1 for model selection and grouped candidate macro F1 as a tiebreaker.")
    table(["Model / family", "Key settings", "CV F1", "Top-1", "Cont.", "Test F1", "Loss", "ms"],
          [[DETAILS[k][0] + " / " + DETAILS[k][1],
            ", ".join(f"{p}={m['config'][p]}" for p in list(m["config"])[:3]),
            f"{m['cv_macro_f1']:.4f}", f"{m['student']['top1']:.4f}",
            f"{m['student']['continuity']:.4f}", f"{m['student']['macro_f1']:.4f}",
            f"{m['student']['log_loss']:.4f}", f"{m['student']['inference_seconds']*1000:.1f}"]
           for k, m in models.items()], [125, 106, 43, 44, 41, 45, 40, 36])
    paragraph("Top-1 is micro-averaged across aligned student observations and includes candidate misses. Continuity averages per-trip direct adjacency or same-arc rates. F1 and log loss use binary candidate labels; F1 uses a 0.5 threshold. Inference time is total classifier scoring and top-1 selection across ten trips, excluding feature extraction and decoding. The decision tree led untuned student top-1. Histogram gradient boosting led grouped F1 among untuned models. Sources: models.json and protocol.json.")

    section(3, "Individual Model Documentation")
    for index, (key, model) in enumerate(models.items()):
        if index == 3:
            story.append(PageBreak())
            paragraph("3. Individual Model Documentation (continued)", "Heading1")
        title, _, rationale, objective = DETAILS[key]
        fit = mean(row["fit_macro_f1"] for row in gaps[key])
        validation = mean(row["validation_macro_f1"] for row in gaps[key])
        student = model["student"]
        paragraph(title, "Heading2")
        paragraph(rationale)
        paragraph("Objective: " + objective)
        paragraph("Fitting settings: " + ", ".join(f"{k}={v}" for k, v in model["config"].items()) +
                  f". Refit on {protocol['training_rows']:,} candidate rows; {model['fit_seconds']:.2f} s.")
        paragraph(f"Student-test top-1 {student['top1']:.4f}, candidate F1 {student['macro_f1']:.4f}, "
                  f"log loss {student['log_loss']:.4f}, precision {student['precision']:.4f}, recall {student['recall']:.4f}.")
        finding = ("The fit/held-out gap is consistent with some overfitting to fitting trips." if fit - validation >= .025
                   else "The fit/held-out gap is small on these folds." if abs(fit-validation) < .025
                   else "Held-out F1 exceeds apparent fit F1 on average; the different trip mixes affect the comparison.")
        if key == "naive_bayes":
            finding += " Its low fit and validation F1 relative to the other models suggest model bias or an unsuitable probability assumption."
        paragraph(f"Generalization evidence: fit F1 {fit:.4f}, held-out F1 {validation:.4f}, gap {fit-validation:+.4f}. "
                  + finding + " This is a comparison of observed fold scores, with fit rows sampled and validation trips fully scored.")

    section(4, "Model Visualisations")
    figure("report_comparisons.png", "Comparison from the actual run. Source: models.json.", height=230)
    figure("report_confusion.png", "Student-test confusion counts. Shading is normalized by actual class. Source: models.json.", height=205)
    figure("report_generalization.png", "Apparent fit versus held-out macro F1 after reproducing the grouped folds. Source: generalization.json.", height=112)
    paragraph("The experiment recorded no epoch-wise training and validation loss histories. The plotted generalization scores are fold summaries.")

    section(5, "Bayesian Hyperparameter Optimisation")
    config = search["config"]
    paragraph(f"{config['sampler']} with seed {config['seed']} used {config['startup_trials']} startup trials and {len(search['history'])} completed trials. "
              f"The objective maximized {config['objective'].lower()}. Max depth and minimum leaf size regulate tree complexity. "
              "Both use inclusive integer ranges with step 1. The original and tuned models use the same validation splits and student-test metrics.")
    table(["Parameter", "Range", "Selected"],
          [[parameter, f"{spec[1]} to {spec[2]}", search["best"][parameter]]
           for parameter, spec in config["space"].items()])
    table(["Trial", "Settings", "CV F1", "Time (s)"],
          [[row["number"], ", ".join(f"{k}={v}" for k, v in row["params"].items()),
            f"{row['score']:.5f}", f"{row['seconds']:.2f}"] for row in search["history"]],
          [55, 250, 85, 80])
    table(["Classifier", "CV F1", "Top-1", "Test F1", "Log loss", "Infer (ms)"],
          [[DETAILS[k][0], f"{models[k]['cv_macro_f1']:.5f}", f"{models[k]['student']['top1']:.5f}",
            f"{models[k]['student']['macro_f1']:.5f}", f"{models[k]['student']['log_loss']:.5f}",
            f"{models[k]['student']['inference_seconds']*1000:.2f}"] for k in ("decision_tree", "tuned")],
          [130, 65, 65, 65, 70, 75])
    paragraph("Tuning improved measured CV F1, student top-1 and student candidate F1 and lowered log loss. The small elapsed-time difference comes from a single run. Full fold-level results and distributions are retained in bayesian.json.")

    section(6, "HMM and Viterbi Route Reconstruction")
    paragraph("A hidden state is a directed candidate arc with its projected fraction u. The emission log weight is log(clip(p, 1e-5, 1)) - 0.5*(d/sigma)^2, where p is the trained candidate probability and d is its GPS residual. These are log potentials used for path ranking.")
    paragraph("For different arcs, L = (1-u_prev)*len_prev + shortest_path(prev.end, cur.start) + u_cur*len_cur. For the same arc use the absolute signed projected progress, with max(0, -progress-12)/beta as a backward penalty. The transition log weight is -abs(L-D)/beta minus this penalty, with D the GPS displacement. An unreachable or over-distance transition scores negative infinity. The distance cap is min(450, max(70, 65*elapsed)) metres.")
    paragraph("Viterbi updates S_t(j) = E_t(j) + max_i[S_(t-1)(i) + T(i,j)]. The best prior score minus a restart penalty is also eligible. Backpointers recover observation arcs, and directed shortest-path bridges insert intervening arcs. Missing candidates return null. Invalid rows, nonpositive elapsed time and gaps above 30 seconds reset the chain. Restarts preserve a matched observation as a new leg when a connection is implausible.")
    table(["Pipeline", "Mean trip top-1", "Direct continuity", "Sequence F1"],
          [[name, *[f"{record['mean_by_trip'][key]:.4f}" for key in ("top1", "continuity", "sequence_f1")]]
           for name, record in [("Classifier", baseline), ("Classifier + Viterbi", trial)]],
          [155, 105, 105, 105])
    paragraph("The selected grid setting had beta 15 m, sigma 35 m and restart penalty 10. Sequence F1 uses the longest common subsequence of collapsed arc sequences; mean scores weight trips equally.")
    for metric in ("top1", "sequence_f1"):
        changes = [(trial["trips"][k][metric] - value[metric], k) for k, value in baseline["trips"].items()]
        delta, trip = min(changes)
        paragraph(f"For {metric}, {sum(value < 0 for value, _ in changes)} trips regressed and "
                  f"{sum(value == 0 for value, _ in changes)} tied. Lowest change was {delta:+.4f} on trip {trip}.")
    paragraph("Large GPS gaps and false local connections can affect path reconstruction. All three tested decoder configurations and per-trip results are retained in decoder.json.")

    section(7, "Geographical Visualisation Using Folium")
    figure("folium_student_prediction.png",
           "Actual Folium rendering for student-test trip 00000000. GPS is blue, roads grey, reference green, and reconstruction orange. Start/end markers and layer controls are visible.")
    paragraph("Interactive companion: results/student_prediction_map.html. Rebuild with evaluation.compare_decoder and capture with deployment.capture. The API map omits the private reference layer.")

    section(8, "API, UI and Deployment")
    figure("development_ui.png", "Chrome screenshot of the real development UI using the FastAPI service over separate localhost ports.", height=230)
    paragraph(f"Observed HTTP {http['http_status']} for trip {http['trip_id']}, {http['observations']:,} observations "
              f"and {http['legs']} route legs. The API logs and structured response summary are included as development_api.log and development_http.json. "
              "The ten student-test trips also passed the API contract. Ground-truth loading occurs after inference, and UI responses contain only predictions and aggregates.")
    paragraph("The workspace contains ten evaluator trips. The official demonstration evidence is pending: Laptop 1 serving FastAPI, Laptop 2 serving the UI, a successful CMD response screenshot from the receiving laptop, and matching server logs. Record the deployed commit so the demonstration can be checked against the submitted source. See README.md for deployment and REQUIREMENTS_CHECKLIST.md for the audit.")
    paragraph("AI assistance: Codex assisted with implementation, experiment execution, diagnostics and report drafting. The records and derived figures come from executed code. Team review and the ability to explain the implementation are required before submission.")

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#415769"))
        canvas.drawString(54, 30, "PATHSNAP | Technical report | Development evidence")
        canvas.drawRightString(A4[0] - 54, 30, str(doc.page))

    SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=54, rightMargin=54,
                      topMargin=46, bottomMargin=44, title="PathSnap Technical Report").build(
        story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path, default=Path("PathSnap-Technical-Report.pdf"))
    args = parser.parse_args()
    build(args.results, args.output)
