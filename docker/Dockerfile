# Training image: multi-stage, non-root, pinned base, model weights baked in.
# Build from the repo root:
#   docker build -f docker/Dockerfile --build-arg GIT_COMMIT=$(git rev-parse --short=7 HEAD) -t <image>:sha-<commit> .
FROM python:3.12-slim-trixie AS base
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY requirements-train.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements-train.txt
# Download the pinned model once at build time so training runs offline on the same revision.
ENV HF_HOME=/opt/hf
ARG HF_MODEL=prajjwal1/bert-mini
ARG HF_REVISION=5e123abc2480f0c4b4cac186d3b3f09299c258fc
RUN /opt/venv/bin/python -c "from huggingface_hub import snapshot_download as s; s('$HF_MODEL', revision='$HF_REVISION')"

FROM base AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf HF_HUB_OFFLINE=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=1000:1000 /opt/hf /opt/hf
COPY requirements-train.txt params.yaml ./
COPY src/ ./src/
COPY data/raw/*.dvc ./data/raw/
COPY data/processed/ ./data/processed/
RUN useradd --uid 1000 --create-home trainer && mkdir -p models && chown -R trainer /app
USER 1000
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT RUNNER=docker
CMD ["python", "src/train.py"]
