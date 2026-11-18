"""Reusable development and prediction maps."""
import folium
import numpy as np


def make_map(trip, nearby=(), reference=(), predicted=()):
    gps = trip.track[trip.good, :2][:, ::-1].tolist()
    result = folium.Map(location=gps[0] if gps else [0, 0], zoom_start=14,
                        tiles="OpenStreetMap")
    if gps:
        layer = folium.FeatureGroup(name="GPS observations").add_to(result)
        delta = np.diff(trip.track[:, 2])
        boundaries = np.flatnonzero(~np.isfinite(delta) | (delta <= 0) | (delta > 30)) + 1
        legs = [leg[:, [1, 0]].tolist() for leg in np.split(trip.track, boundaries)
                if len(leg) >= 2]
        if legs:
            folium.PolyLine(legs, color="#2859c5", weight=2, opacity=.55, dash_array="4 5").add_to(layer)
        stride = max(1, (len(gps) + 349) // 350)
        for point in gps[::stride]:
            folium.CircleMarker(point, radius=2, color="#2859c5", fill=True).add_to(layer)
        folium.Marker(gps[0], tooltip="GPS start").add_to(layer)
        folium.Marker(gps[-1], tooltip="GPS end").add_to(layer)
        result.fit_bounds(gps)
    for name, ids, color, weight in (
        ("Nearby roads", nearby, "#68758b", 2),
        ("Reference route", reference, "#168257", 7),
        ("Predicted route", predicted, "#d34916", 4),
    ):
        lines = [trip.nodes[trip.arcs[i], ::-1].tolist() for i in ids if i >= 0]
        if lines:
            layer = folium.FeatureGroup(name=name).add_to(result)
            folium.PolyLine(lines, color=color, weight=weight, opacity=.8).add_to(layer)
    folium.LayerControl(collapsed=False).add_to(result)
    return result
