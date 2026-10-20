"""Shared tokenisation and prediction for train.py and evaluate.py."""
import torch
from torch.utils.data import DataLoader, TensorDataset


def setup_determinism(seed: int) -> None:
    """Same seed + deterministic ops + fixed thread count = identical CPU runs."""
    from transformers import set_seed

    set_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(4)


def encode(tok, df, max_length: int) -> TensorDataset:
    e = tok(list(df["text"]), truncation=True, max_length=max_length,
            padding="max_length", return_tensors="pt")
    return TensorDataset(e["input_ids"], e["attention_mask"], torch.tensor(df["label"].values))


def predict(model, tok, df, max_length: int) -> list[int]:
    model.eval()
    preds = []
    with torch.no_grad():
        for ids, mask, _ in DataLoader(encode(tok, df, max_length), batch_size=256):
            preds += model(input_ids=ids, attention_mask=mask).logits.argmax(-1).tolist()
    return preds
