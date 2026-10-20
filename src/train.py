"""Fine-tune the pinned HF model and log the run to MLflow.

Run: python src/train.py [--learning_rate 3e-5 --epochs 3 ...]  (CLI overrides params.yaml)
Tracking server comes from MLFLOW_TRACKING_URI; it is never hard-coded.
"""
import argparse
import os
import subprocess
from pathlib import Path

import mlflow
import pandas as pd
import torch
import yaml
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from model_utils import encode, predict, setup_determinism

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = "question-detection"


def git_commit() -> str:
    if os.environ.get("GIT_COMMIT"):  # Docker/K8s have no .git
        return os.environ["GIT_COMMIT"]
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def dvc_md5(dvc_file: Path) -> str:
    """Raw-data md5 from the .dvc pointer: the link between MLflow and DVC."""
    try:
        return yaml.safe_load(dvc_file.read_text())["outs"][0]["md5"]
    except Exception:
        return "untracked"


def load_params() -> dict:
    p = yaml.safe_load((ROOT / "params.yaml").read_text())["train"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--learning_rate", type=float)
    for key in ("epochs", "batch_size", "max_length", "random_seed"):
        parser.add_argument(f"--{key}", type=int)
    for key, value in vars(parser.parse_args()).items():
        if value is not None:
            p[key] = value
    # MLflow stores params as text ("5e-05"); reproduce.py writes them back, so cast here.
    p["learning_rate"] = float(p["learning_rate"])
    for key in ("epochs", "batch_size", "max_length", "random_seed", "num_labels"):
        p[key] = int(p[key])
    return p


def main() -> None:
    p = load_params()
    setup_determinism(p["random_seed"])
    train = pd.read_parquet(ROOT / "data/processed/train.parquet")
    test = pd.read_parquet(ROOT / "data/processed/test.parquet")
    tok = AutoTokenizer.from_pretrained(p["hf_model"], revision=p["hf_revision"])
    model = AutoModelForSequenceClassification.from_pretrained(
        p["hf_model"], revision=p["hf_revision"], num_labels=p["num_labels"])

    mlflow.set_experiment(EXPERIMENT)
    run_name = f"bert-mini-lr{p['learning_rate']:g}-ep{p['epochs']}-len{p['max_length']}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(p)  # seed, model name and revision are params, not tags
        mlflow.set_tags({"git_commit": git_commit(),
                         "dvc_raw_md5": dvc_md5(ROOT / "data/raw/dataset.parquet.dvc"),
                         "runner": os.environ.get("RUNNER", "laptop")})
        if os.environ.get("REPRODUCES"):
            mlflow.set_tag("reproduces", os.environ["REPRODUCES"])
        mlflow.log_input(mlflow.data.from_pandas(train, source="data/processed/train.parquet",
                                                 targets="label", name="train"), context="training")

        loader = DataLoader(encode(tok, train, p["max_length"]), batch_size=p["batch_size"], shuffle=True,
                            generator=torch.Generator().manual_seed(p["random_seed"]))
        opt = torch.optim.AdamW(model.parameters(), lr=p["learning_rate"])
        model.train()
        step = 0
        for _ in range(p["epochs"]):
            for ids, mask, y in loader:
                loss = model(input_ids=ids, attention_mask=mask, labels=y).loss
                loss.backward()
                opt.step()
                opt.zero_grad()
                step += 1
                if step % 50 == 0:
                    mlflow.log_metric("train_loss", loss.item(), step=step)

        preds = predict(model, tok, test, p["max_length"])
        acc = accuracy_score(test["label"], preds)
        f1 = f1_score(test["label"], preds, average="macro")
        # Explicit pip_requirements: auto-detection looks for torchvision and crashes on CPU-only torch.
        info = mlflow.transformers.log_model({"model": model, "tokenizer": tok}, name="model",
                                             task="text-classification",
                                             pip_requirements=str(ROOT / "requirements-train.txt"))
        mlflow.log_metric("accuracy", acc, model_id=info.model_id)
        mlflow.log_metric("f1", f1, model_id=info.model_id)

        model.save_pretrained(ROOT / "models/model")  # DVC output read by evaluate.py
        tok.save_pretrained(ROOT / "models/model")
        (ROOT / "models/run_id.txt").write_text(run.info.run_id + "\n")
        print(f"run_id={run.info.run_id} model_id={info.model_id} accuracy={acc:.4f} f1={f1:.4f}")


if __name__ == "__main__":
    main()
