"""FastAPI service for the final evaluator workflow."""
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import joblib
import numpy as np

from api.inference import predict
from data_processing.trips import load_reference, trips
from evaluation.metrics import route_metrics
from evaluation.reference import align_reference
from visualizations.maps import make_map

log = logging.getLogger("uvicorn.error")


def evaluate(directory, prediction):
    if not (directory / f"{directory.name}.route").is_file():
        return None
    reference = load_reference(directory, prediction.trip)
    labels, _ = align_reference(prediction.trip, reference)
    return route_metrics(prediction.decoded.points, prediction.sample.ids, labels,
                         prediction.trip.arcs, reference, prediction.decoded.route)


def create_app(root, artifact, origins=(), partition="evaluator_test"):
    @asynccontextmanager
    async def lifespan(app):
        directories = trips(root, partition)
        if len(directories) != 10:
            raise RuntimeError(f"Expected 10 trips in {root / partition}, found {len(directories)}")
        app.state.trips = {entry.name: entry for entry in directories}
        app.state.bundle = joblib.load(artifact)
        yield

    app = FastAPI(title="PathSnap", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.get("/trips")
    def list_trips():
        return {"trips": sorted(app.state.trips)}

    @app.post("/trips/{trip_id}/prediction")
    def run_prediction(trip_id: str):
        directory = app.state.trips.get(trip_id)
        if directory is None:
            raise HTTPException(status_code=404, detail="Trip not found")
        log.info("Processing %s trip %s", partition, trip_id)
        try:
            prediction = predict(directory, app.state.bundle)
            metrics = evaluate(directory, prediction)
            decoded = prediction.decoded
            map_html = make_map(prediction.trip, nearby=np.unique(prediction.sample.ids[:, :3]),
                                predicted=decoded.route).get_root().render()
        except (OSError, ValueError) as error:
            log.exception("Failed to process trip %s", trip_id)
            raise HTTPException(status_code=500, detail="Trip data could not be processed") from error
        log.info("Processed trip %s with %d route legs", trip_id, len(decoded.legs))
        return {"trip_id": trip_id, "observation_arcs": [int(i) if i >= 0 else None for i in decoded.points],
                "route_legs": decoded.legs, "metrics": metrics, "map_html": map_html}

    return app


app = create_app(
    Path(os.getenv("PATHSNAP_DATA", "../Student folder")),
    Path(os.getenv("PATHSNAP_ARTIFACT", "artifacts/pathsnap.joblib")),
    tuple(origin.strip() for origin in os.getenv(
        "PATHSNAP_UI_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",")),
)
