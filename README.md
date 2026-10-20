# mlops-u1 — question vs keyword query classifier

Mini MLOps platform for VU MIF MLOps assignment U1: a reproducible DVC pipeline that fine-tunes
[`prajjwal1/bert-mini`](https://huggingface.co/prajjwal1/bert-mini) to tell natural-language
questions/statements from keyword queries, logging every run to an MLflow server running in a local
`kind` Kubernetes cluster.

| Deliverable | Link |
| --- | --- |
| Repo + tag | https://github.com/nsannn/mlops-u1 · tag `u1-final` |
| Requirements | [docs/requirements.md](docs/requirements.md) |
| Training image (GHCR) | [`ghcr.io/nsannn/mlops-u1/train:sha-474a8cd`](https://github.com/users/nsannn/packages/container/package/mlops-u1%2Ftrain) · [size](docs/image-size.md) · [Trivy scan](docs/security-scan.md) |
| Kubernetes manifests | [k8s/](k8s/) |
| Report | [docs/u1-report.md](docs/u1-report.md) |

## Run from zero

Prerequisites: WSL2 Ubuntu, Docker Desktop (WSL integration on), `uv`, `kind`, `kubectl`, `gh`.

```bash
git clone https://github.com/nsannn/mlops-u1.git && cd mlops-u1
uv venv .venv --python 3.12 && source .venv/bin/activate
uv pip sync --index-strategy unsafe-best-match requirements.txt
```

_Pipeline, cluster and MLflow steps are added as they are implemented._

## Layout

| Path | Contents |
| --- | --- |
| `src/` | pipeline code: prepare, train, evaluate |
| `scripts/` | one-off helpers (data download) |
| `docker/` | Dockerfiles (training image, MLflow server) |
| `k8s/` | kind cluster config and Kubernetes manifests |
| `docs/` | requirements, architecture, scan results, report |

## Ports and logins

_Added with the cluster (Step 4)._
