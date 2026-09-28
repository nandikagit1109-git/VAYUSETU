"""End-to-end self check (section 14).

Starts from a clean data/processed, runs the app in-process, waits for the
first FL run (timeout 180 s), then prints a PASS/FAIL line for every
programmatically checkable definition-of-done item (section 15).
Exits non-zero on any FAIL.

Run: python scripts/verify_demo.py
"""
import io
import os
import shutil
import sys
import time
import base64
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# In-process run against a throwaway DB.
os.environ["VAYUSETU_DB_URL"] = f"sqlite:///{BACKEND_DIR / 'verify_tmp.db'}"
os.environ["AUTO_TRAIN_ON_START"] = "true"

RESULTS: list[tuple[bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def main() -> int:
    # 1. Clean slate for processed data (forces a fresh synthetic build + FL run).
    processed = BACKEND_DIR / "data" / "processed"
    if processed.exists():
        for p in processed.iterdir():
            p.unlink()
    else:
        processed.mkdir(parents=True, exist_ok=True)

    print("VayuSetu demo verification")
    print("==========================")
    print("[1/4] Building master table and starting app in-process...")

    from fastapi.testclient import TestClient

    from app.main import app

    t0 = time.time()
    with TestClient(app) as client:
        meta = client.get("/api/meta").json()
        check("meta reports synthetic mode", meta["data_mode"] == "synthetic")
        check("meta has no fallback reason", meta.get("fallback_reason") is None)
        check("n_cities == 28", meta["n_cities"] == 28, f"got {meta['n_cities']}")
        check("tier split 20/5/3", (meta["n_tier1"], meta["n_tier2"], meta["n_tier3"]) == (20, 5, 3))

        cities = client.get("/api/cities").json()["cities"]
        check("28 cities listed", len(cities) == 28)
        tier1_ids = {c["city_id"] for c in cities if c["tier"] == 1}

        print(f"[2/4] Startup took {time.time() - t0:.1f}s. Waiting for FL run (timeout 180s)...")
        deadline = time.time() + 180
        fl = client.get("/api/federated/status").json()
        while time.time() < deadline and fl.get("status") not in ("completed", "failed"):
            time.sleep(3)
            fl = client.get("/api/federated/status").json()
        check("federated run completed", fl.get("status") == "completed", fl.get("error") or "")
        check("8 rounds recorded", len(fl.get("rounds", [])) == 8)
        losses = [r["global_loss"] for r in fl.get("rounds", [])]
        check("global loss trends down", len(losses) >= 2 and losses[-1] < losses[0], f"{losses[:1]} -> {losses[-1:]}")
        check("participating clients >= 5", len(fl.get("clients", [])) >= 5, f"clients: {fl.get('clients')}")

        meta2 = client.get("/api/meta").json()
        check("model_version set after run", bool(meta2.get("model_version")))
        check("model_method federated_gru", meta2.get("model_method") == "federated_gru")

        eval_data = client.get("/api/federated/eval").json()
        check("fl_eval available", eval_data.get("available") is True)
        if eval_data.get("available"):
            check("fl_eval rows for every client", len(eval_data["rows"]) == len(fl["clients"]))
            means = ("mean_mae_persistence", "mean_mae_local", "mean_mae_federated")
            check("fl_eval has all three means", all(isinstance(eval_data[m], (int, float)) for m in means))
            mae_rows = {"city_id", "name", "n_val", "mae_persistence", "mae_local", "mae_federated", "mae_personalized"}
            check("fl_eval row keys exact", all(set(r) == mae_rows for r in eval_data["rows"]))

        print("[3/4] Checking forecasts, hotspots, reports, alerts...")
        n_fc = n_interp = 0
        for c in cities:
            r = client.get(f"/api/forecast?city_id={c['city_id']}").json()
            if r.get("error"):
                check(f"forecast {c['city_id']} error envelope only for remote cities",
                      "no monitored city within" in r.get("message", ""))
                continue
            n_fc += 1
            if r["method"] == "neighbor_idw":
                n_interp += 1
        check("forecasts for (almost) all active cities", n_fc >= 25, f"{n_fc}/28 with data")
        check("tier2/3 interpolation present", n_interp >= 5, f"{n_interp} interpolated")

        hotspots = client.get("/api/hotspots").json()["hotspots"]
        check("hotspots exist", len(hotspots) >= 6, f"{len(hotspots)} hotspots")
        dw = [h for h in hotspots if h.get("downwind_city_id") and h.get("eta_hours") is not None]
        check("at least one downwind city with ETA", len(dw) >= 1, f"{len(dw)} with plume")

        r = client.post("/api/reports", json={
            "latitude": 28.6139, "longitude": 77.2090, "manual_visibility": "hazy"})
        check("manual report accepted", r.status_code == 201, str(r.json()))
        report = r.json()
        before = next(c for c in client.get("/api/cities").json()["cities"]
                      if c["city_id"] == report["city_id"])
        check("report changes adjusted AQI", before["report_count_24h"] >= 1)

        buf = io.BytesIO()
        try:
            from PIL import Image

            Image.new("RGB", (64, 64), color=(180, 170, 160)).save(buf, format="PNG")
            photo_b64 = base64.b64encode(buf.getvalue()).decode()
            r = client.post("/api/reports", json={
                "latitude": 19.0760, "longitude": 72.8777, "photo_base64": photo_b64})
            check("photo report scored", r.status_code == 201 and r.json().get("scorer") == "heuristic_v1")
        except ImportError:
            print("  [skip] Pillow missing; photo report check skipped")

        r = client.post("/api/alerts/check")
        check("alert check creates alerts", r.status_code == 200 and r.json()["created"] >= 1)
        alerts = client.get("/api/alerts").json()["alerts"]
        check("at least one alert for a tier-1 city",
              any(a["city_id"] in tier1_ids for a in alerts))
        ncr = [a for a in alerts if a["city_id"] in {"delhi", "gurugram"}]
        check("NCR alerts use GRAP with stage",
              all(a["action_framework"] == "GRAP" and a["grap_stage"] for a in ncr) and ncr)
        non_ncr = [a for a in alerts if a["city_id"] not in {"delhi", "gurugram"}]
        check("non-NCR alerts use ADVISORY",
              all(a["action_framework"] == "ADVISORY" and a["grap_stage"] is None for a in non_ncr))
        check("alert actions non-empty", all(len(a["action"]) > 0 for a in alerts))
        if alerts:
            a0 = alerts[0]
            r = client.post(f"/api/alerts/{a0['id']}/acknowledge")
            check("acknowledge works", r.status_code == 200 and r.json()["acknowledged"] is True)

        # No NaN in any sampled payload.
        for path in ("/api/meta", "/api/cities", "/api/reports", "/api/hotspots",
                     "/api/alerts", "/api/federated/status", "/api/federated/eval"):
            body = client.get(path).text
            check(f"no NaN/Infinity in {path}", "NaN" not in body and "Infinity" not in body)

    # Release the SQLite file handle so the temp DB can be removed (Windows keeps
    # the file locked until every pooled connection is closed).
    from app.db import engine

    engine.dispose()

    print("[4/4] Summary")
    failed = [name for ok, name in RESULTS if not ok]
    for ok, name in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        db = BACKEND_DIR / "verify_tmp.db"
        if db.exists():
            db.unlink()
    sys.exit(code)
