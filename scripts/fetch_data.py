"""Download the Kaggle data once and keep a seeded, class-balanced sample.

Run: python scripts/fetch_data.py   (needs ~/.kaggle/kaggle.json)
Output: data/raw/dataset.parquet, then tracked with `dvc add`.
"""
import subprocess
from pathlib import Path

import pandas as pd

SLUG = "stefanondisponibile/quora-question-keyword-pairs"  # Kaggle version 1, 2021-01-19
N_ROWS, SEED = 10_000, 42
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    tmp = ROOT / "data/kaggle"  # gitignored download folder
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run(["kaggle", "datasets", "download", SLUG, "-f", "train.tsv", "-p", str(tmp)], check=True)
    src = next(tmp.glob("train.tsv*"))  # plain or .zip; pandas reads both
    df = (pd.read_csv(src, sep="\t")[["query", "target"]]
          .rename(columns={"query": "text", "target": "label"})
          .dropna())
    df = df.groupby("label", group_keys=False).sample(n=N_ROWS // 2, random_state=SEED)
    out = ROOT / "data/raw/dataset.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(df.shape, df["label"].value_counts().to_dict())


if __name__ == "__main__":
    main()
