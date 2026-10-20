"""Evaluate models/model on the test split, write metrics.json and attach eval/* to the training run."""
import json
from pathlib import Path

import mlflow
import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from model_utils import predict, setup_determinism

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = yaml.safe_load((ROOT / "params.yaml").read_text())["train"]
    setup_determinism(int(p["random_seed"]))
    tok = AutoTokenizer.from_pretrained(ROOT / "models/model")
    model = AutoModelForSequenceClassification.from_pretrained(ROOT / "models/model")
    test = pd.read_parquet(ROOT / "data/processed/test.parquet")
    y, preds = test["label"], predict(model, tok, test, int(p["max_length"]))
    metrics = {"accuracy": accuracy_score(y, preds),
               "f1": f1_score(y, preds, average="macro"),
               "precision": precision_score(y, preds, average="macro"),
               "recall": recall_score(y, preds, average="macro")}
    out = json.dumps(metrics, indent=2) + "\n"
    (ROOT / "metrics.json").write_text(out)
    print(out)

    run_id_file = ROOT / "models/run_id.txt"
    if run_id_file.exists():  # evaluation metrics land on the training run
        try:
            client = mlflow.MlflowClient()
            run_id = run_id_file.read_text().strip()
            for key, value in metrics.items():
                client.log_metric(run_id, f"eval/{key}", value)
        except Exception as exc:  # server may be unreachable
            print(f"warning: eval metrics not attached ({exc})")


if __name__ == "__main__":
    main()
