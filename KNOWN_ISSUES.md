# KNOWN_ISSUES.md

Honest deviations and concerns, per the build protocol (record, never silently
work around).

- **Photo scorer is a heuristic, not a trained model.** `cv_scorer.py`
  (`"heuristic_v1"`) is a stand-in for a trained haze-classification CNN: the
  offline demo cannot ship model weights. The UI labels every photo score
  "heuristic estimate, not a measurement" (section 2, honest labeling).
- **SMS is simulated.** Alert channels include `sms_simulated`; no real SMS is
  sent in v3. The UI labels these "simulated".
- **GRAP action strings are paraphrased.** `grap_rules.py` stores short
  paraphrases for demonstration; verify against the latest CAQM GRAP
  notification before any real-world use (comment also at top of that file).
- **Federated does not always beat persistence per city.** Results in
  `fl_eval.json` are reported exactly as measured (spec instruction: do not
  tune anything to make federated win). With a 14-day input window the
  persistence baseline is strong; the personalized model closes most of the
  gap between local-only and federated.
- **Real-data mode is exercised by tests and fallback logic, not by live
  CPCB/POWER/FIRMS runs.** The fetch scripts are manual, opt-in, and require
  internet/keys; no real raw files were available offline, so the real loader
  paths are verified by unit tests and the fallback reason mechanism only.
- **`verify_demo.py` runs in-process via TestClient**, not a real uvicorn
  socket; production parity is covered by the docker healthcheck and the
  deployed Render service.
- **Docker was not runnable on the original build machine** (no Docker
  daemon); compose/Dockerfile changes are validated by inspection and the
  deployed Render blueprint, not by a local `docker compose up`.
- **SQLite in a background thread**: the FL runner never touches the DB
  directly; evaluate/status writes go through files, and DB sessions are
  created per request/per thread as required (section 12).
