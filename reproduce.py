"""Re-create a historical MLflow run: python reproduce.py <run_id>   (needs MLFLOW_TRACKING_URI)

Five steps: read the run -> checkout its commit -> same data bytes -> its params -> dvc repro,
then compare metrics within a tolerance. The repo is always restored to the starting branch.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import mlflow
import yaml

TOL = 0.005
ROOT = Path(__file__).resolve().parent


def sh(*cmd, **kw):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=True, text=True, **kw)


def main(run_id: str) -> None:
    t0 = time.time()
    old = mlflow.get_run(run_id)  # 0. the record: tags, params, metrics
    if sh("git", "status", "--porcelain", capture_output=True).stdout.strip():
        sys.exit("Working tree is dirty: commit or stash first")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD", capture_output=True).stdout.strip()
    new_id = None
    try:
        sh("git", "checkout", "-q", old.data.tags["git_commit"])  # 1. code + pointers at that time
        # 2. same raw-data bytes from the local cache; only *.dvc pointers, because that commit
        #    may predate dvc.lock and repro --force rebuilds every stage output anyway
        pointers = [str(p.relative_to(ROOT)) for p in ROOT.glob("data/raw/*.dvc")]
        sh("dvc", "checkout", "--force", *pointers)
        params = yaml.safe_load((ROOT / "params.yaml").read_text())  # 3. run params -> params.yaml
        params["train"].update({k: yaml.safe_load(v) for k, v in old.data.params.items()
                                if k in params["train"]})
        (ROOT / "params.yaml").write_text(yaml.safe_dump(params, sort_keys=False))
        sh("dvc", "repro", "--force", env={**os.environ, "REPRODUCES": run_id})  # 4. new run
        new_id = (ROOT / "models/run_id.txt").read_text().strip()
        new = mlflow.get_run(new_id)
        for m in ("accuracy", "f1"):  # 5. compare with tolerance
            d = abs(new.data.metrics[m] - old.data.metrics[m])
            print(f"{m}: old={old.data.metrics[m]:.4f} new={new.data.metrics[m]:.4f} delta={d:.4f}")
            assert d <= TOL, f"{m} delta {d:.4f} > {TOL}"
    finally:
        sh("git", "checkout", "-q", "--", ".")  # drop the repro edits
        sh("git", "checkout", "-q", branch)
        sh("dvc", "checkout", "--force")
    print(f"Reproduced {run_id} as {new_id} in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main(sys.argv[1])
