# U1 report — question vs keyword query classifier

Nojus Sandovas · 2026-10-21 · repo https://github.com/nsannn/mlops-u1, tag `u1-final`

## What was done

| Req. | Result | Evidence |
| --- | --- | --- |
| R1 Repo + requirements | `src/ docker/ k8s/ docs/`; README run-from-zero (rehearsed from a fresh clone, 195 s); `requirements.md` v1.4: 5 FR, 17 NFR with KPI, reproduction NFR-08..10 | [README](../README.md), [requirements](requirements.md) |
| R2 Reproducible pipeline | `dvc.yaml` prepare → train → evaluate, `params.yaml`, `dvc.lock` committed, DVC local remote synced; 3 runs with different hyperparameters (best accuracy 0.997); `reproduce.py` 81.7 s, Δ 0.0000 | [evidence](evidence.md) |
| R3 Docker image | Multi-stage, non-root (UID 1000), `ghcr.io/nsannn/mlops-u1/train:sha-474a8cd`, 1 982 MB, Trivy 0 CRITICAL / 46 HIGH reviewed, SBOM | [image-size](image-size.md), [security-scan](security-scan.md) |
| R4 Cluster + MLflow | `kind` cluster from `k8s/kind-config.yaml`, namespace `mlops`, PostgreSQL + MLflow Deployments with PVCs, NodePort → `localhost:5000`; laptop runs stored on the cluster; data survives pod deletion | [k8s/](../k8s/), [architecture](architecture.md), [evidence](evidence.md) |
| Extensions | None yet (E1–E3 planned) | — |

Model: `prajjwal1/bert-mini` (11M params) fine-tuned on CPU on a seeded 10k sample of Kaggle
*Quora Question Keyword Pairs* (license listed as Unknown, coursework only). The published
`shahrukhx01/bert-mini-finetune-question-detection` (0.997) is the reference; our best run matches it.

## What did not work at first

| Problem | Fix |
| --- | --- |
| `Auto*` classes could not load bert-mini (config has no `model_type`) | Explicit `BertTokenizerFast` / `BertForSequenceClassification` |
| `mlflow.transformers.log_model` needed `torchvision` with CPU-only torch | Pass `pip_requirements=requirements-train.txt` |
| `reproduce.py` failed on commits without `dvc.lock`, then left a detached HEAD | Check out only raw-data `.dvc` pointers; restore with `git checkout -f` |
| MLflow init container hung: `pg_isready` had no user for UID 1000 | `pg_isready -U mlflow` |
| `No module named 'psycopg'`: SQLAlchemy 2.1 maps `postgresql://` to psycopg v3 | `postgresql+psycopg2://` URI |
| MLflow `OOMKilled` at 2 GiB (several server workers) | `--workers=1`, 3 GiB limit (uses ~1.7 GB) |
| NFR-03 missed: 66 s run at `max_length` 32 | Default `max_length` 16: 42 s, accuracy 0.9945 |
| Not fixed: `cryptography` HIGH CVE — `mlflow==3.15.2` pins `cryptography<50` | Documented as accepted risk |

Open: the GHCR package must be switched to public by hand (no API for it); the image is 1.98 GB,
right at its 2 GB target (torch CPU dominates).

## Time spent

| Part | Time |
| --- | --- |
| Tool setup, repo, model/data choice (20 Oct evening) | ~1.5 h |
| R1 repo + requirements | ~0.3 h |
| R2 pipeline, debugging, reproduction | ~0.5 h |
| R3 image, scan, GHCR | ~0.3 h |
| R4 cluster + MLflow, debugging | ~0.5 h |
| Graded runs, evidence, README rehearsal, report | ~0.7 h |
| **Total** | **~3.8 h** |

Times from commit timestamps (21 Oct 00:23–01:40) plus the setup evening; adjust if your own count differs.
