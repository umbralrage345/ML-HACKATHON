"""Capture development evidence with Chrome and a real local HTTP exchange."""
import argparse
import base64
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen

from websocket import create_connection


def wait(callback, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = callback()
            if value:
                return value
        except OSError:
            pass
        time.sleep(.3)
    raise RuntimeError(f"Timed out: {callback}")


def capture(args):
    api = "http://127.0.0.1:8123"
    ui = "http://127.0.0.1:8124"
    with ExitStack() as stack:
        profile = stack.enter_context(tempfile.TemporaryDirectory(ignore_cleanup_errors=True))

        def spawn(command, log=subprocess.DEVNULL):
            child = subprocess.Popen(command, stdout=log, stderr=log)
            def close():
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
            stack.callback(close)

        log = stack.enter_context((args.output / "development_api.log").open("w", encoding="utf-8"))
        code = ("from pathlib import Path; import uvicorn; from api.app import create_app; "
                f"app=create_app(Path({str(args.data)!r}),Path('artifacts/pathsnap.joblib'),[{ui!r}],"
                "partition='student_test'); uvicorn.run(app,host='127.0.0.1',port=8123)")
        spawn([sys.executable, "-c", code], log)
        spawn([sys.executable, "-m", "http.server", "8124", "--bind", "127.0.0.1", "--directory", "ui"])
        spawn([sys.executable, "-m", "http.server", "8125", "--bind", "127.0.0.1",
               "--directory", str(args.output)])
        wait(lambda: urlopen(api + "/trips", timeout=2).read())
        wait(lambda: urlopen(ui, timeout=2).read())
        spawn([str(args.chrome), "--headless", "--disable-gpu", "--no-first-run",
               "--remote-debugging-port=0", "--window-size=1360,900", f"--user-data-dir={profile}", ui])
        port = wait(lambda: (Path(profile) / "DevToolsActivePort").read_text().partition("\n")[0])
        pages = json.load(urlopen(f"http://127.0.0.1:{port}/json/list"))
        ws = create_connection(next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page"),
                               suppress_origin=True, timeout=20)
        stack.callback(ws.close)
        request_id = 0

        def cdp(method, **params):
            nonlocal request_id
            request_id += 1
            ws.send(json.dumps(dict(id=request_id, method=method, params=params)))
            while True:
                message = json.loads(ws.recv())
                if message.get("id") == request_id:
                    if "error" in message:
                        raise RuntimeError(message["error"])
                    return message["result"]

        def evaluate(expression, **options):
            response = cdp("Runtime.evaluate", expression=expression, returnByValue=True, **options)
            if "exceptionDetails" in response:
                raise RuntimeError(response["exceptionDetails"])
            return response["result"].get("value")

        def screenshot(filename):
            result = cdp("Page.captureScreenshot", format="png")
            (args.output / filename).write_bytes(base64.b64decode(result["data"]))

        wait(lambda: evaluate("document.readyState === 'complete' && !!document.querySelector('#connect')"))
        evaluate(f"document.querySelector('#server').value={api!r}; document.querySelector('#connect').requestSubmit()")
        wait(lambda: evaluate("document.querySelector('#trip').options.length === 10"))
        evaluate("document.querySelector('#run').requestSubmit()")
        wait(lambda: evaluate("!document.querySelector('#map').hidden && !document.querySelector('#metrics').hidden"))
        assert evaluate("!document.querySelector('#map').srcdoc.includes('Reference route')")
        time.sleep(3)  # Allow the sandboxed map frame to paint.
        screenshot("development_ui.png")

        request = Request(
            api + "/trips/00000000/prediction", method="POST")
        with urlopen(request, timeout=35) as response:
            result = json.load(response)
            evidence = dict(http_status=response.status, trip_id=result["trip_id"],
                            observations=len(result["observation_arcs"]),
                            legs=len(result["route_legs"]), metrics=result["metrics"])
        (args.output / "development_http.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        cdp("Page.navigate", url="http://127.0.0.1:8125/student_prediction_map.html")
        wait(lambda: evaluate("!!document.querySelector('.leaflet-control-layers-list') && "
                              "document.querySelectorAll('.leaflet-overlay-pane path').length > 10"))
        try:
            wait(lambda: evaluate("Array.from(document.querySelectorAll('img.leaflet-tile')).some(i => i.complete && i.naturalWidth > 0)"), timeout=8)
        except RuntimeError:
            print("Basemap tiles unavailable; data overlays rendered.")
        screenshot("folium_student_prediction.png")
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results"))
    capture(parser.parse_args())
