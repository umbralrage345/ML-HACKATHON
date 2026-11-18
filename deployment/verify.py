"""Exercise the evaluator HTTP contract on the ten development holdout trips."""
import argparse
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app


def verify(data, artifact):
    origin = "http://localhost:8080"
    with TestClient(create_app(data, artifact, [origin], partition="student_test")) as client:
        listing = client.get("/trips", headers={"Origin": origin})
        listing.raise_for_status()
        assert listing.headers["access-control-allow-origin"] == origin
        assert client.post("/trips/unknown/prediction").status_code == 404
        options = listing.json()["trips"]
        assert len(options) == len(set(options)) == 10
        for trip in options:
            response = client.post(f"/trips/{trip}/prediction")
            response.raise_for_status()
            payload = response.json()
            assert set(payload) == {"trip_id", "observation_arcs", "route_legs", "metrics", "map_html"}
            assert payload["trip_id"] == trip
            assert payload["route_legs"]
            assert len(payload["observation_arcs"]) == payload["metrics"]["observations"]
            assert "Predicted route" in payload["map_html"]
            assert "Reference route" not in payload["map_html"]
            print(f"{trip}: {len(payload['observation_arcs'])} observations", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, default=Path("artifacts/pathsnap.joblib"))
    args = parser.parse_args()
    verify(args.data, args.artifact)
