# PathSnap

PathSnap matches noisy GPS traces to directed road arcs. A supervised candidate classifier scores each observation, then a Viterbi decoder uses the road network to reconstruct connected route legs. The evaluator interface fetches trips from FastAPI and displays the predicted route and server-computed metrics.

## Reproduce the development run

Use Python 3.13 for the supplied artifacts. Run these commands from this repository with the supplied dataset in the parent directory.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m data_processing.explore --data "../Student folder"
python -m training.prepare --data "../Student folder"
python -m training.experiment
python -m evaluation.compare_decoder --data "../Student folder"
python -m evaluation.feature_sensitivity
python -m deployment.verify --data "../Student folder"
```

The development root contains `train/<trip_id>/` and `student_test/<trip_id>/`. Each directory stores files named after the trip ID with extensions `.track`, `.nodes`, `.arcs`, and `.route`. The exploration command writes partition summaries, a detailed inventory, plots, and an interactive Folium map to `results/`. The original inventory command is also available as `python data_processing/inspect_dataset.py --data "../Student folder" --output results/dataset_inventory.csv`.

Model fitting uses every second observation in each fitting trip, three trip-disjoint folds, and full validation trips. Scaling is fitted inside each fold where applicable. Candidate classification, observation ranking, and sequence metrics are recorded separately. The fixed-seed Optuna TPE search uses grouped training folds only and retains every trial. See [the technical notes](TECHNICAL.md) for label alignment, evaluation, and decoder details.

Generated candidates are stored in the ignored `artifacts/candidates/` directory. Model weights and the deployment bundle are written to `artifacts/`. Use artifacts produced by a trusted training run. Loading a Joblib artifact executes Python deserialization, so use the same package versions as the training machine.

## Evaluator deployment

On laptop 1, put the ten official trips in an external `evaluator_test/` directory with the same trip layout. Supply the directory **containing** `evaluator_test/` through `PATHSNAP_DATA`. Start the backend from this repository.

```powershell
$env:PATHSNAP_DATA = "C:/PathSnap/final-data"
$env:PATHSNAP_ARTIFACT = "artifacts/pathsnap.joblib"
$env:PATHSNAP_UI_ORIGINS = "http://localhost:8080"
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
```

On laptop 2, start the UI from its copy of the checkout.

```powershell
python -m http.server 8080 --bind 127.0.0.1 --directory ui
```

Open `http://localhost:8080` on laptop 2. Enter laptop 1's LAN address and port, select **Connect**, choose a trip, and select **Reconstruct route**. The laptops need a reachable connection on API port 8000. Folium loads its browser assets and basemap tiles over the internet.

`GET /trips` lists the published trip IDs. `POST /trips/{trip_id}/prediction` returns observation arc IDs, reconstructed route legs, aggregate metrics when a valid reference is available, and a prediction map. Ground-truth data stays on laptop 1. The API logs each request, and startup validates the ten-trip inventory. The verification command exercises the same API contract with the ten student-test trips as a development integration check.

## Rebuild the technical report

Install the additional report tools and run these commands after the development run. Chrome is required for the screenshots. The capture uses separate local HTTP ports and the student-test partition.

```powershell
python -m pip install -r requirements-report.txt
python -m evaluation.generalization
python -m deployment.capture --data "../Student folder" --chrome "C:/Program Files/Google/Chrome/Application/chrome.exe"
python -m reporting.build
```

See the [requirements audit](REQUIREMENTS_CHECKLIST.md) for the differences between local evidence and the official demonstration. During the official LAN run, save the UI screenshot and FastAPI logs, and capture the successful response in CMD on the receiving laptop. To keep the response screenshot readable, use this command in CMD and substitute an official trip ID.

```cmd
powershell -NoProfile -Command "$r=Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/trips/TRIP_ID/prediction'; $r | Select-Object trip_id,@{n='observations';e={$_.observation_arcs.Count}},@{n='route_legs';e={$_.route_legs.Count}},metrics | ConvertTo-Json -Depth 4"
```

Save the server logs and record the deployed Git commit on both laptops so the final evidence can be tied to the submitted source.
