# Requirements — question vs keyword query classifier

Version: 1.3
Date: 2026-10-21
Author: Nojus Sandovas

## 1. Scope

### 1.1 Problem

A search system receives two kinds of input: keyword queries ("bert mini size") and natural-language
questions or statements ("how big is bert mini?"). Only the second kind should be routed to an
expensive question-answering reader; keyword queries go to plain keyword search. Routing everything
to the reader wastes compute and lowers answer quality.

This project trains a small binary text classifier that makes the routing decision, and builds the
MLOps platform around it: versioned data and pipeline (DVC), experiment tracking (MLflow) on a
self-hosted server in a local Kubernetes cluster, and a containerised training image.

### 1.2 Stakeholders

| Stakeholder | Interest | Priority |
| --- | --- | --- |
| Search users | Correct, fast answers | High |
| Search platform team | Lower reader compute cost | High |
| ML engineer (author) | Reproducible, traceable experiments | High |
| Course lecturer | Verifiable pipeline and evidence | High |

### 1.3 Use cases

| ID | Use case | Actor | Result |
| --- | --- | --- | --- |
| UC-01 | Classify an incoming query | Search service | Query type + probability |
| UC-02 | Train a new model version | ML engineer | MLflow run with model, metrics, lineage tags |
| UC-03 | Reproduce a historical experiment | ML engineer / auditor | New run with equivalent metrics |

## 2. Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | The model classifies an input text as keyword query or question/statement and returns the class probability | Must |
| FR-02 | `dvc repro` builds the model from the pinned raw data through `prepare → train → evaluate` | Must |
| FR-03 | Every training run logs params, metrics, the dataset digest, `git_commit` and `dvc_raw_md5` tags and the model to the MLflow server in the cluster | Must |
| FR-04 | `python reproduce.py <run_id>` re-creates a chosen historical run and reports the metric difference | Must |
| FR-05 | Training can run as a container image and as a Kubernetes Job | Should |

## 3. Non-functional requirements

| ID | Category | Requirement | KPI | Measurement / evidence |
| --- | --- | --- | --- | --- |
| NFR-01 | Quality | Test accuracy | ≥ 0.95 (reference model: 0.997) | `metrics.json` |
| NFR-02 | Quality | Macro F1 on the test split | ≥ 0.95 | `metrics.json` |
| NFR-03 | Performance | Training time on CPU (4 threads, 8k rows) | ≤ 60 s | MLflow run duration |
| NFR-04 | Performance | Single-query CPU inference latency | p95 ≤ 50 ms | Load test (U2) |
| NFR-05 | Size | Saved model weights | ≤ 60 MB | `du -sh models/model` |
| NFR-06 | Data | Training sample is reproducible from the pinned source | Same md5 on every fetch with seed 42 | `dvc add` md5 vs `.dvc` file |
| NFR-07 | Security | Secrets in Git (Kaggle token, DB passwords) | 0 | `git ls-files` review before tagging |

### 3.1 Experiment tracking and reproducibility (v1.1)

| ID | Category | Requirement | KPI | Measurement / evidence |
| --- | --- | --- | --- | --- |
| NFR-08 | Reproducibility | Any historical run is re-created by `python reproduce.py <run_id>` | < 2 min, \|Δaccuracy\| ≤ 0.005 | `time python reproduce.py <id>` output in `docs/u1-report.md` |
| NFR-09 | Traceability | Runs carrying `git_commit` and `dvc_raw_md5` tags | 100 % of runs | MLflow UI filter |
| NFR-10 | Data version | `dvc.lock` raw-data md5 equals the run's `dvc_raw_md5` tag | 100 % of runs | Compared live in the demo |

Measured 2026-10-21 ([`u1-report.md`](u1-report.md)): NFR-08 reproduction 81.7 s, Δaccuracy 0.0000; NFR-09 and
NFR-10 100 % of 4 runs. NFR-01/02: best run accuracy 0.997, macro F1 0.997. NFR-03: MLflow run duration
(training + evaluation + model logging) is 66 s at `max_length` 32 — **misses the 60 s target by 6 s** — and 42 s at
`max_length` 16. Options: accept 16 as default, or raise the target to 75 s with this justification.

### 3.2 Containerisation (v1.2)

| ID | Category | Requirement | KPI | Measured (2026-10-21) | Evidence |
| --- | --- | --- | --- | --- | --- |
| NFR-11 | Size | Training image size | ≤ 2 000 MB | 1 982 MB — pass, little headroom | [`image-size.md`](image-size.md) |
| NFR-12 | Security | CRITICAL CVEs in the published image | 0 | 0 (46 HIGH reviewed) | [`security-scan.md`](security-scan.md) |
| NFR-13 | Security | Container runtime user | UID ≠ 0 | UID 1000 | `docker run --rm <image> id -u` |
| NFR-14 | Traceability | Published image tags | 100 % `sha-<commit>`, never `latest` | `sha-474a8cd` only | GHCR package page |

### 3.3 Kubernetes and MLflow server (v1.3)

| ID | Category | Requirement | KPI | Measured (2026-10-21) | Evidence |
| --- | --- | --- | --- | --- | --- |
| NFR-15 | Durability | MLflow runs and artifacts after deleting the MLflow and PostgreSQL pods | 100 % kept | 100 % (test run + artifact intact) | `kubectl delete pod` test, `docs/u1-report.md` |
| NFR-16 | Availability | MLflow ready after `kubectl apply` (images present) | ≤ 120 s | 22 s | `kubectl wait --for=condition=Available` |
| NFR-17 | Tracking | Runs logged from the laptop are stored on the cluster server | 100 %, no local `mlruns/` | Artifact URIs `mlflow-artifacts:/…` | MLflow UI |

## 4. KPI summary

- Model: accuracy ≥ 0.95, macro F1 ≥ 0.95 (NFR-01, NFR-02).
- System: training ≤ 60 s on CPU, inference p95 ≤ 50 ms (NFR-03, NFR-04).
- Business: share of keyword queries kept away from the reader — not measured in this course project.

## 5. Assumptions and constraints

- Model: [`prajjwal1/bert-mini`](https://huggingface.co/prajjwal1/bert-mini) (~11M parameters, MIT),
  revision `5e123abc2480f0c4b4cac186d3b3f09299c258fc`, fine-tuned on CPU.
- Reference baseline: [`shahrukhx01/bert-mini-finetune-question-detection`](https://huggingface.co/shahrukhx01/bert-mini-finetune-question-detection)
  (same architecture, 0.997 reported test accuracy, no license tag; used only for comparison).
- Data: Kaggle [`stefanondisponibile/quora-question-keyword-pairs`](https://www.kaggle.com/datasets/stefanondisponibile/quora-question-keyword-pairs),
  version 1 (2021-01-19). Kaggle lists its license as **Unknown**; it is used for coursework only.
  A seeded, class-balanced 10k-row sample of `train.tsv` is used.
- Infrastructure: one laptop (WSL2, Docker Desktop), local `kind` cluster, no GPU.

## 6. Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Dataset license is unknown | Medium | Medium | Coursework only; documented here; replaceable by an openly licensed set |
| Training too slow for the reproduction limit | Medium | High | Small model, 10k-row sample, `max_length` 32 |
| Task is easy, so runs differ little | Medium | Low | Vary learning rate, epochs and sequence length |
| Kaggle unavailable later | Low | Medium | Data bytes kept in the DVC remote |

## 7. Change history

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | 2026-10-21 | Nojus Sandovas | Initial requirements: scope, FR-01..05, NFR-01..07 |
| 1.1 | 2026-10-21 | Nojus Sandovas | MLflow + DVC pipeline: reproduction and traceability NFR-08..10 |
| 1.2 | 2026-10-21 | Nojus Sandovas | Training image on GHCR: container NFR-11..14 with measured values |
| 1.3 | 2026-10-21 | Nojus Sandovas | kind cluster with PostgreSQL + MLflow: NFR-15..17 |
