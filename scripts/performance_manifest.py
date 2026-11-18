"""Stamp sanitized source and built-asset provenance for a frozen local cohort.

This is separate from performance_environment.application_fingerprint, which
hashes runtime files directly and detects drift during a capacity run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from performance_environment import ROOT


def manifest():
    app = ROOT / "apps/ia_maturity"
    paths = []
    for directory in (app / "ia_maturity", app / "grc/src"):
        for path in directory.rglob("*"):
            relative = path.relative_to(app).as_posix()
            if (path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
                    and not relative.startswith("ia_maturity/public/grc/")
                    and relative not in {"ia_maturity/www/grc.html", "ia_maturity/www/grc-site.html"}):
                paths.append(path)
    paths.extend([app / "grc/index.html", app / "grc/vite.config.ts"])
    source = {path.relative_to(app).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)}
    assets = {path.relative_to(app).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((app / "ia_maturity/public/grc").rglob("*")) if path.is_file()}
    return {"base_commit": subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip(),
        "source_files": source, "assets": assets,
        "source_sha256": hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(),
        "assets_sha256": hashlib.sha256(json.dumps(assets, sort_keys=True).encode()).hexdigest(),
        "scope": "Frozen local performance implementation; no destination deployment claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(ROOT / "diagnostics/performance-20261113") or output.suffix != ".json":
        raise ValueError("Write only sanitized manifest JSON in the local diagnostics directory.")
    result = manifest()
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"source_files": len(result["source_files"]), "assets": len(result["assets"]),
        "source_sha256": result["source_sha256"], "assets_sha256": result["assets_sha256"]}))


if __name__ == "__main__":
    main()
