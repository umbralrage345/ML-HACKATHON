# PathSnap

PathSnap is a map-matching project for reconstructing vehicle routes from GPS observations and a road network. This checkout currently contains the dataset inspection utility and its output.

## Dataset inspection

Use Python 3.8 or later. The inspection utility uses the Python standard library. From the repository root, with the supplied dataset in the parent directory, run:

```powershell
python data_processing/inspect_dataset.py --data "../Student folder" --output results/dataset_inventory.csv
```

The dataset directory must contain `train/` and `student_test/`. The utility writes one CSV row per trip, including counts, coordinate bounds, timestamp gaps, and reference integrity checks.

## Repository layout

| Directory | Intended contents |
| --- | --- |
| `data_processing/` | Dataset inspection, preprocessing, and candidate generation |
| `features/` | Feature extraction and preparation |
| `training/` | Model training scripts and notebooks |
| `evaluation/` | Metrics, comparisons, and diagnostic plots |
| `optimization/` | Bayesian search code, configurations, and trial records |
| `route_reconstruction/` | HMM and Viterbi decoding |
| `api/` | Inference API and model loading |
| `ui/` | Evaluator interface |
| `deployment/` | Two-laptop deployment configuration |
| `visualizations/` | Folium maps and plot generation |
| `results/` | Dataset inventory, experiment logs, and result summaries |
| `artifacts/` | Saved model and inference configuration |

The application folders are placeholders pending the team implementation. Deployment instructions depend on the application's final entry points and inference artifacts.
