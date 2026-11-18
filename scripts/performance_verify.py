"""Verify local source/asset provenance, safe delivery and retained rollback build.

Read-only loopback HTTP and file/hash checks. Outputs no response bodies/cookies.
Run after the sustained capacity window, not during unrelated acceptance jobs.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

import requests

from performance_environment import ROOT, guard
from performance_fixture import STATE

APP = ROOT / "apps/ia_maturity"
EVIDENCE = ROOT / "diagnostics/performance-20261113"
BASE = "0caa5504a189b65aa68f3ffa1c198f8be1fccfc7"


def checked_file(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Manifest path escapes its app root.")
    return path


def get(client, url, **kwargs):
    response = client.get(url, timeout=120, allow_redirects=False, **kwargs)
    return response


def verify():
    configuration = guard()
    manifest = json.loads((EVIDENCE / "final-source-manifest.json").read_text())
    result = {"scope": "read-only local delivery and retained baseline rollback rehearsal", "checks": {}}
    checks = result["checks"]
    checks["fixture_mail_remains_muted"] = configuration.get("mute_emails") == 1
    checks["fixture_scheduler_remains_paused"] = configuration.get("pause_scheduler") == 1
    for category in ("source_files", "assets"):
        changed = [name for name, digest in manifest[category].items()
            if not checked_file(APP, name).is_file()
            or hashlib.sha256(checked_file(APP, name).read_bytes()).hexdigest() != digest]
        result[category + "_count"] = len(manifest[category])
        result[category + "_mismatch_paths"] = changed
        checks[category + "_match_final_manifest"] = not changed
    result["final_manifest_sha256"] = hashlib.sha256((EVIDENCE / "final-source-manifest.json").read_bytes()).hexdigest()
    snapshot = EVIDENCE / "baseline-app"
    tree = subprocess.check_output(["git", "-C", str(APP), "ls-tree", "-rz", BASE])
    mismatches, count = [], 0
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, encoded_name = entry.split(b"\t", 1)
        mode, kind, expected = metadata.decode().split()
        if kind != "blob":
            continue
        count += 1
        name = encoded_name.decode()
        path = checked_file(snapshot, name)
        data = path.read_bytes() if path.is_file() else b""
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            mismatches.append(name)
    checks["baseline_tracked_files_match_retained_commit"] = not mismatches
    result.update(baseline_commit=BASE, baseline_tracked_file_count=count, baseline_mismatch_paths=mismatches)
    public = requests.Session()
    content = get(public, "http://127.0.0.1:8013/api/method/ia_maturity.grc.public.site_content")
    conditional = get(public, "http://127.0.0.1:8013/api/method/ia_maturity.grc.public.site_content",
        headers={"If-None-Match": content.headers.get("ETag", "")})
    checks["public_content_private_revalidation_304"] = (content.status_code == 200
        and "private" in content.headers.get("Cache-Control", "")
        and "no-cache" in content.headers.get("Cache-Control", "") and conditional.status_code == 304)
    state = json.loads(STATE.read_text())
    admin = requests.Session()
    admin.cookies.update(state["users"]["admin"]["cookies"])
    private = get(admin, "http://127.0.0.1:8013/api/method/ia_maturity.grc.api.bootstrap")
    checks["private_api_no_store"] = private.status_code == 200 and "no-store" in private.headers.get("Cache-Control", "")
    for name, client in (("anonymous", public), ("authenticated", admin)):
        missing = get(client, "http://127.0.0.1:8013/assets/ia_maturity/grc/assets/missing-AbCdEf12.js")
        checks[name + "_missing_asset_not_publicly_cached"] = (missing.status_code >= 400
            and "no-store" in missing.headers.get("Cache-Control", "")
            and "immutable" not in missing.headers.get("Cache-Control", ""))
    static_name = next(name for name in manifest["assets"] if re.search(r"/index-[^/]+\.js$", name))
    asset_path = "/assets/ia_maturity/" + static_name.split("/public/", 1)[1]
    identity = get(public, "http://127.0.0.1:8013" + asset_path, headers={"Accept-Encoding": "identity"})
    compressed = get(public, "http://127.0.0.1:8013" + asset_path,
        headers={"Accept-Encoding": "gzip"}, stream=True)
    encoded = compressed.raw.read(decode_content=False)
    compressed.close()
    checks["static_real_gzip_equal_decoded_body"] = compressed.headers.get("Content-Encoding") == "gzip" and gzip.decompress(encoded) == identity.content
    checks["static_length_vary_immutable_without_cookie"] = (len(encoded) == int(compressed.headers.get("Content-Length", -1))
        and "Accept-Encoding" in compressed.headers.get("Vary", "")
        and "immutable" in compressed.headers.get("Cache-Control", "") and "Set-Cookie" not in compressed.headers)
    result["static_decoded_bytes"] = len(identity.content)
    result["static_gzip_bytes"] = len(encoded)
    baseline_page = get(public, "http://127.0.0.1:8014/grc-site")
    checks["retained_baseline_page_serves"] = baseline_page.status_code == 200
    baseline_main = re.search(r'src="([^\"]+/index-[^\"]+\.js)"', baseline_page.text)
    checks["retained_baseline_matching_asset_serves"] = bool(baseline_main
        and get(public, "http://127.0.0.1:8014" + baseline_main.group(1)).status_code == 200)
    result["all_checks_pass"] = all(checks.values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    if not output.is_relative_to(EVIDENCE) or output.suffix != ".json":
        raise ValueError("Write only sanitized JSON evidence under the local diagnostics directory.")
    result = verify()
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not result["all_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
