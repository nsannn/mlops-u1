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

1. **Environment**

   ```bash
   git clone https://github.com/nsannn/mlops-u1.git && cd mlops-u1
   uv venv .venv --python 3.12 && source .venv/bin/activate
   uv pip sync --index-strategy unsafe-best-match requirements.txt
   ```

2. **Data.** On the author's machine the DVC remote is `~/dvcstore`: run `dvc pull`. Elsewhere,
   rebuild the sample from Kaggle (needs `~/.kaggle/kaggle.json`) with `python scripts/fetch_data.py`,
   then `dvc status` must report no change to `data/raw/dataset.parquet`.

3. **Cluster + MLflow** (kind, namespace `mlops`, PostgreSQL + MLflow with PVCs)

   ```bash
   kind create cluster --config k8s/kind-config.yaml
   kubectl apply -f k8s/namespace.yaml
   kubectl create secret generic mlflow-db -n mlops \
     --from-literal=POSTGRES_USER=mlflow --from-literal=POSTGRES_DB=mlflow \
     --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)"
   MLFLOW_IMAGE=$(grep -o 'mlflow-server:sha-[0-9a-f]*' k8s/mlflow.yaml)
   docker build -f docker/Dockerfile.mlflow -t "$MLFLOW_IMAGE" docker/
   kind load docker-image "$MLFLOW_IMAGE" --name mlops
   kubectl apply -f k8s/postgres.yaml -f k8s/mlflow.yaml
   kubectl wait --for=condition=Available deploy --all -n mlops --timeout=300s
   curl http://localhost:5000/health        # OK
   ```

4. **Train and track in the cluster**

   ```bash
   export MLFLOW_TRACKING_URI=http://localhost:5000
   dvc repro                                # prepare -> train -> evaluate
   python reproduce.py <run_id>             # re-creates a run in < 2 min
   ```

5. **Tear down:** `kind delete cluster --name mlops` (this also deletes the PVC data).

## Layout

| Path | Contents |
| --- | --- |
| `src/` | pipeline code: prepare, train, evaluate |
| `scripts/` | one-off helpers (data download) |
| `docker/` | Dockerfiles (training image, MLflow server) |
| `k8s/` | kind cluster config and Kubernetes manifests |
| `docs/` | requirements, architecture, scan results, report |

## Ports and logins

| What | Where | Login |
| --- | --- | --- |
| MLflow UI + API | http://localhost:5000 (kind maps host 5000 → NodePort 30500 → Service `mlflow`) | none |
| MLflow in-cluster | `http://mlflow.mlops.svc.cluster.local:5000` | none |
| PostgreSQL | `postgres.mlops.svc:5432`, cluster-internal only | user `mlflow`; password in Secret `mlflow-db`: `kubectl get secret mlflow-db -n mlops -o jsonpath='{.data.POSTGRES_PASSWORD}' \| base64 -d` |
| Alternative access | `kubectl port-forward -n mlops svc/mlflow 5000:5000` | none |

## Where to look

- Experiments: MLflow UI → experiment `question-detection`.
- Latest metrics: [`metrics.json`](metrics.json); pipeline graph: `dvc dag`.
- Artifacts physically: PVC `mlflow-artifacts`, a `local-path` volume under `/var/local-path-provisioner/`
  inside the `mlops-control-plane` container. They survive pod restarts, but not `kind delete cluster`.
