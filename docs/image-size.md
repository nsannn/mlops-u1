# Training image — size and identity

| Field | Value |
| --- | --- |
| Image | `ghcr.io/nsannn/mlops-u1/train:sha-474a8cd` |
| Digest | `sha256:4adca4914e231b6088f58b0aea726efea9827ffe532f67cd3ba0cabfd1404377` |
| Built from commit | `474a8cd` (feat(docker): multi-stage non-root training image) |
| Platform | linux/amd64 |
| Built | 2026-10-21 00:41 (EEST) |
| Size (`docker image inspect .Size`) | 1 981 885 584 B ≈ **1 982 MB** |
| Python venv `/opt/venv` | 1 863 MB (torch 2.14.1+cpu is most of it) |
| Baked model `/opt/hf` (prajjwal1/bert-mini) | 44 MB |
| Runtime user | UID 1000 (`trainer`), checked with `docker run --rm <image> id -u` |

Measured on Docker 29.9.1 (Docker Desktop, WSL2). MB = 1 000 000 bytes.

## Why it is this big

The image already uses the CPU-only torch wheel; the default CUDA build would add several GB.
What remains is torch's own CPU libraries plus the full `mlflow` package. Possible reductions, not
done for U1: `mlflow-skinny` instead of `mlflow`, or exporting the model to ONNX for a separate,
much smaller inference image (U2).

## Smoke test

```bash
docker run --rm -e MLFLOW_TRACKING_URI=sqlite:////tmp/m.db ghcr.io/nsannn/mlops-u1/train:sha-474a8cd
# run_id=6826fd8f... accuracy=0.9960 f1=0.9960   (offline, ~73 s including startup)
```
