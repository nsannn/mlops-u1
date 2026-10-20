"""Split the raw sample into stratified train/test files. Run: python src/prepare_data.py"""
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = yaml.safe_load((ROOT / "params.yaml").read_text())["prepare"]
    df = pd.read_parquet(ROOT / "data/raw/dataset.parquet")
    train, test = train_test_split(df, test_size=p["test_size"], random_state=p["seed"], stratify=df["label"])
    out = ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    train.to_parquet(out / "train.parquet", index=False)
    test.to_parquet(out / "test.parquet", index=False)
    print(f"train={len(train)} test={len(test)}")


if __name__ == "__main__":
    main()
