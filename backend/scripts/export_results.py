"""Export FL results to CSV for the research write-up.

Reads data/processed/fl_status.json and fl_eval.json (both written by a
completed federated run) and writes:

- results/fl_eval.csv      per-city persistence/local/federated/personalized MAE + means
- results/convergence.csv  per-round global loss and validation MAE

Run: python scripts/export_results.py   (from backend/, after a completed run)
"""
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROCESSED = BACKEND_DIR / "data" / "processed"
RESULTS = BACKEND_DIR / "results"


def _load(name: str) -> dict | None:
    try:
        with open(PROCESSED / name, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        print(f"warning: could not read {name}: {exc}", file=sys.stderr)
        return None


def export_eval(eval_data: dict) -> Path:
    out = RESULTS / "fl_eval.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["city_id", "name", "n_val", "mae_persistence", "mae_local",
                    "mae_federated", "mae_personalized"])
        for r in eval_data.get("rows", []):
            w.writerow([r.get("city_id"), r.get("name"), r.get("n_val"),
                        r.get("mae_persistence"), r.get("mae_local"),
                        r.get("mae_federated"), r.get("mae_personalized")])
        means = eval_data
        w.writerow(["MEAN", "", "", means.get("mean_mae_persistence"),
                    means.get("mean_mae_local"), means.get("mean_mae_federated"),
                    means.get("mean_mae_personalized")])
    return out


def export_convergence(status: dict) -> Path:
    out = RESULTS / "convergence.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["round", "global_loss", "global_val_mae",
                    "mean_client_train_loss", "n_clients"])
        for r in status.get("rounds", []):
            losses = r.get("client_losses", {})
            mean_loss = sum(losses.values()) / len(losses) if losses else ""
            w.writerow([r.get("round"), r.get("global_loss"), r.get("global_val_mae"),
                        round(mean_loss, 6) if mean_loss != "" else "",
                        len(losses)])
    return out


def main() -> int:
    eval_data = _load("fl_eval.json")
    status = _load("fl_status.json")
    if not eval_data and not status:
        print("Nothing to export: run a federated training first "
              "(POST /api/federated/run) so fl_status.json / fl_eval.json exist.")
        return 1
    RESULTS.mkdir(parents=True, exist_ok=True)
    if eval_data and eval_data.get("available"):
        print(f"wrote {export_eval(eval_data)}")
    if status and status.get("rounds"):
        print(f"wrote {export_convergence(status)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
