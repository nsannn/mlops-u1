# Architecture (U1)

All MLflow state lives on two PVCs in the `kind` cluster, so deleting either pod loses nothing.
The laptop, the browser and (in U2) an in-cluster training Job all reach the same `mlflow` Service.

```mermaid
flowchart LR
    subgraph laptop["Laptop · WSL2 Ubuntu"]
        git["Git repo<br/>code, params.yaml, dvc.lock"]
        dvc["dvc repro<br/>prepare → train → evaluate"]
        store[("DVC remote<br/>~/dvcstore")]
        browser["Browser<br/>localhost:5000"]
        docker["docker build<br/>training image"]
    end

    kaggle[("Kaggle<br/>quora-question-keyword-pairs v1")]
    hf[("Hugging Face<br/>prajjwal1/bert-mini @ 5e123abc")]
    ghcr[("GHCR<br/>train:sha-474a8cd")]

    subgraph kind["kind cluster · namespace mlops"]
        svc["Service mlflow<br/>NodePort 30500 ← host :5000"]
        mlflow["Deployment mlflow<br/>mlflow server, 1 worker"]
        pvca[("PVC mlflow-artifacts<br/>/mlartifacts: models, files")]
        pgsvc["Service postgres<br/>ClusterIP :5432"]
        pg["Deployment postgres<br/>16.4-alpine"]
        pvcp[("PVC postgres-data<br/>runs, params, metrics, tags")]
        secret["Secret mlflow-db"]
    end

    kaggle -->|fetch_data.py, seeded 10k sample| dvc
    hf -->|pinned revision| dvc
    dvc <-->|dvc push / pull, md5| store
    git --- dvc
    dvc -->|MLFLOW_TRACKING_URI| svc
    browser --> svc
    docker -->|push sha-commit tag| ghcr
    svc --> mlflow
    mlflow --> pvca
    mlflow -->|SQL| pgsvc --> pg --> pvcp
    secret -.-> mlflow
    secret -.-> pg
```

## Lineage

| Dimension | Owner | Link in each MLflow run |
| --- | --- | --- |
| Code | Git | tag `git_commit` |
| Data bytes | DVC (`data/raw/dataset.parquet.dvc`, `dvc.lock`) | tag `dvc_raw_md5`, dataset digest via `log_input` |
| Configuration | `params.yaml` | run params (incl. model name, revision, seed) |
| Environment | `requirements*.txt`, training image | LoggedModel `requirements.txt`; image tag `sha-<commit>` |
| Model | MLflow LoggedModel on PVC | `model_id`, `models/run_id.txt` in Git |
