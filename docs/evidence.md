# U1 evidence — runs, reproduction, persistence

Detailed evidence behind [`u1-report.md`](u1-report.md). Collected 2026-10-21.

## README rehearsal from a fresh clone

`git clone` from GitHub into an empty folder, then only the README commands, on a temporary second
cluster (`mlops-rehearsal`, host port 5002, `localhost:5002` added to `--allowed-hosts` in that copy only)
so the graded cluster stayed untouched:

```text
dvc pull                         -> Data and pipelines are up to date
kind create + secret + build/load + apply -> mlflow, postgres Available; /health OK
dvc repro                        -> all stages skipped (outputs pulled)
dvc repro --force                -> run b9dca13a, accuracy 0.9945 (max_length 16), 65.3 s
python reproduce.py b9dca13a...  -> delta 0.0000, 57.6 s
total, images cached             -> 195 s
```

Found while rehearsing: a non-5000 port needs its host in `--allowed-hosts` (now noted in the README).

## Experiments on the cluster MLflow server

Experiment `question-detection` on `http://localhost:5000` (MLflow in the `kind` cluster, namespace `mlops`).
Model `prajjwal1/bert-mini` @ `5e123abc`, data sample md5 `a09b3309d69993fe85e0a50297eb573b`, 8 000 train / 2 000 test rows.

| Run ID | Commit | learning_rate | max_length | epochs | accuracy | macro F1 | MLflow run | `dvc repro` wall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ac008c53` | `3ab189b` exp 1 | 1e-4 | 32 | 2 | 0.9960 | 0.9960 | 66.2 s | 83.9 s |
| `514d40c0` | `7059669` exp 2 | 3e-5 | 32 | 2 | **0.9970** | **0.9970** | 66.0 s | 79.1 s |
| `f419d8eb` | `dce8bb4` exp 3 | 1e-4 | 16 | 2 | 0.9945 | 0.9945 | 41.7 s | 53.8 s |
| `4d690bf7` | reproduction of `ac008c53` | 1e-4 | 32 | 2 | 0.9960 | 0.9960 | 66.3 s | 82.8 s |

MLflow run = training + evaluation + model logging (NFR-03 target ≤ 60 s: missed at `max_length` 32, met at 16).

Every run carries `git_commit`, `dvc_raw_md5`, the dataset digest (`log_input`), `eval/*` metrics,
a `train_loss` curve and a LoggedModel (`m-…`) stored as `mlflow-artifacts:/…` on the cluster PVC.
Best run: exp 2 (lower learning rate). Halving `max_length` costs 0.15 pp accuracy but trains 36 % faster.

```text
$ dvc params diff HEAD~2          $ dvc metrics diff HEAD~2
train.max_length  32 -> 16        accuracy  0.996 -> 0.9945  (-0.0015)
```

## NFR-08 — reproduction

```text
$ time python reproduce.py ac008c53959c423ab68b62ee2e7170d8
+ git checkout -q 4b3bb5e3
+ dvc checkout --force data/raw/dataset.parquet.dvc
+ dvc repro --force
accuracy: old=0.9960 new=0.9960 delta=0.0000
f1: old=0.9960 new=0.9960 delta=0.0000
+ git checkout -q -f main
+ dvc checkout --force
Reproduced ac008c53959c423ab68b62ee2e7170d8 as 4d690bf73f3943c888a3acae82043881 in 81.7 s
```

Result: **81.7 s < 120 s**, Δaccuracy = 0.0000 ≤ 0.005. The new run is tagged `reproduces=ac008c53…`.
CPU + fixed seed + deterministic algorithms + 4 threads gives bit-identical metrics.

## NFR-09 / NFR-10 — lineage

All 4 runs have `git_commit` and `dvc_raw_md5` tags (100 %). `dvc.lock` records raw-data md5
`a09b3309d69993fe85e0a50297eb573b`, equal to every run's `dvc_raw_md5` tag (100 %).

## NFR-15 — persistence after pod recreation

```text
$ kubectl delete pod -n mlops -l app=mlflow ; kubectl delete pod -n mlops -l app=postgres
$ kubectl wait --for=condition=Available deploy --all -n mlops
mlflow-69f75d6fd4-9mvh6    1/1  Running  0  22s      # new pods
postgres-5cd6cf5f9-qtr84   1/1  Running  0  22s
```

After the restart all 4 runs, their params, metrics, tags and LoggedModels were still served
(174 MB under `/mlartifacts`). Metadata lives on PVC `postgres-data`, files on PVC `mlflow-artifacts`;
both are `local-path` volumes under `/var/local-path-provisioner/` in the `mlops-control-plane` container.

## Cluster state

```text
$ kubectl get all,pvc -n mlops
pod/mlflow-…    1/1 Running      deployment.apps/mlflow    1/1     service/mlflow    NodePort  5000:30500/TCP
pod/postgres-…  1/1 Running      deployment.apps/postgres  1/1     service/postgres  ClusterIP 5432/TCP
persistentvolumeclaim/mlflow-artifacts  Bound  5Gi  RWO  standard
persistentvolumeclaim/postgres-data     Bound  2Gi  RWO  standard
```

## Problems met so far

| Problem | Cause | Fix |
| --- | --- | --- |
| Tokenizer/model failed to load | `prajjwal1/bert-mini` config has no `model_type`, so `Auto*` classes fail | Explicit `BertTokenizerFast` / `BertForSequenceClassification` |
| `log_model` crashed (`No module named 'torchvision'`) | MLflow dependency inference with CPU-only torch | Pass `pip_requirements=requirements-train.txt` |
| `reproduce.py` failed on old commits | Old commit had no `dvc.lock`; restore failed on untracked `dvc.lock` | Check out only raw-data `.dvc` pointers; restore with `git checkout -f` |
| MLflow init container never finished | UID 1000 has no passwd entry, so `pg_isready` could not pick a user | `pg_isready -U mlflow` |
| MLflow crashed: `No module named 'psycopg'` | SQLAlchemy 2.1 maps `postgresql://` to psycopg v3 | URI `postgresql+psycopg2://` |
| MLflow `OOMKilled` at 2 GiB | Default multiple server workers | `--workers=1`, limit 3 GiB (uses ~1.7 GB) |
| `cryptography` HIGH CVE not fixable | `mlflow==3.15.2` pins `cryptography<50` | Documented as accepted risk |
