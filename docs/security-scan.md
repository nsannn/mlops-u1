# Security scan — training image

| Field | Value |
| --- | --- |
| Image | `ghcr.io/nsannn/mlops-u1/train:sha-474a8cd` (digest `sha256:4adca491…1404377`) |
| Scanner | Trivy 0.74.0, `--scanners vuln --severity HIGH,CRITICAL` |
| Scan date | 2026-10-21 00:43 (EEST) |
| Raw results | [`trivy-train.json`](trivy-train.json), [`trivy-train.txt`](trivy-train.txt) |
| SBOM | [`sbom-train.json`](sbom-train.json) (SPDX JSON) |

## Result

| Severity | Findings | Unique CVEs | Gate |
| --- | --- | --- | --- |
| CRITICAL | **0** | 0 | `trivy image --severity CRITICAL --exit-code 1` → exit 0, **PASS** |
| HIGH | 46 | 10 | Reviewed below |

## HIGH findings and decisions

| Where | Findings | Fix available? | Decision |
| --- | --- | --- | --- |
| Debian 13.7 base packages (util-linux family, ncurses, systemd libs, perl-base, login) — 8 CVEs | 44 | No (Debian has not released fixes) | Accept. The base already runs `apt-get upgrade`; rebuild when Debian ships fixes. None of these tools run in the training job. |
| `cryptography` 49.0.0 — CVE-2026-69247 (PKCS#7 EnvelopedData decryption) | 1 | 50.0.0, **blocked**: `mlflow==3.15.2` requires `cryptography<50` | Accept. Training never decrypts PKCS#7 data. Revisit when the course moves past mlflow 3.15.2. |
| `mlflow` 3.15.2 — CVE-2026-71211 (SSRF via AI Gateway secret) | 1 | No | Accept. The flaw is in the MLflow **server**'s AI Gateway; this image only runs the tracking client. |

## Controls in the image

- Multi-stage build: build tooling stays in the builder stage.
- Non-root runtime user (UID 1000).
- No secrets in the image: `.dockerignore` excludes `.env`, `basic_auth.ini`, `.git`, `.dvc/cache`; credentials are passed at run time.
- Pinned base (`python:3.12-slim-trixie`) and pinned Python dependencies (`requirements-train.txt`).
- Model weights pinned by revision and baked in; the container runs with `HF_HUB_OFFLINE=1`.
