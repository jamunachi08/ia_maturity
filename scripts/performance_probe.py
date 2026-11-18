"""Measure read-only HTTP work on dedicated local Gunicorn performance ports.

Results contain timings, sizes, counts and hashes, never credentials, cookies,
OTP values or response bodies. This is a lab workload, not real-user telemetry.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import threading
import time
from urllib.parse import urlparse

import requests
from performance_environment import ROOT, guard, application_fingerprint
from performance_fixture import STATE


def validate(base_url, output):
    guard()
    url = urlparse(base_url)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or url.port not in (8011, 8012, 8013, 8014):
        raise ValueError("Performance traffic is allowed only on dedicated loopback ports.")
    path = Path(output).resolve()
    if not path.is_relative_to(ROOT / "diagnostics/performance-20261113"):
        raise ValueError("Write sanitized performance evidence only in the local diagnostics directory.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def percentile(values, percent):
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)], 3) if ordered else None


def summarize(samples):
    elapsed = [s["elapsed_ms"] for s in samples]
    return {"samples": len(samples), "status_counts": dict(Counter(str(s["status"]) for s in samples)),
        "p50_ms": percentile(elapsed, 50), "p75_ms": percentile(elapsed, 75), "p95_ms": percentile(elapsed, 95),
        "max_ms": round(max(elapsed), 3) if elapsed else None,
        "p95_sql_queries": percentile([s["queries"] for s in samples if s.get("queries") is not None], 95),
        "p95_bytes": percentile([s["bytes"] for s in samples], 95),
        "redirects": sum(s.get("redirects", 0) for s in samples),
        "semantic_errors": dict(Counter(s["semantic_error"] for s in samples if s.get("semantic_error"))),
        "errors": sum(s["status"] != 200 or bool(s.get("semantic_error")) for s in samples)}


def request(client, url, account=None):
    started = time.perf_counter()
    try:
        response = client.get(url, timeout=120, allow_redirects=True)
        sample = {"status": response.status_code, "elapsed_ms": (time.perf_counter() - started) * 1000,
            "bytes": len(response.content), "queries": int(response.headers["X-GRC-Perf-SQL-Count"])
                if "X-GRC-Perf-SQL-Count" in response.headers else None,
            "server_timing": response.headers.get("Server-Timing", ""),
            "cache_control": response.headers.get("Cache-Control", ""),
            "content_encoding": response.headers.get("Content-Encoding", ""),
            "redirects": len(response.history)}
        path = urlparse(url).path
        protected_api = path in {"/api/method/ia_maturity.grc.api.bootstrap", "/api/method/ia_maturity.grc.api.dashboard"}
        payload = None
        if response.headers.get("Content-Type", "").startswith("application/json") and response.status_code == 200:
            try:
                payload = response.json()
                sample["semantic_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            except ValueError:
                sample["semantic_error"] = "invalid_json"
        if protected_api and response.status_code == 200:
            message = payload.get("message") if isinstance(payload, dict) else None
            if response.history:
                sample["semantic_error"] = "protected_api_redirect"
            elif not isinstance(message, dict) or payload.get("exc") or payload.get("exception"):
                sample["semantic_error"] = "invalid_protected_api_envelope"
            elif path.endswith("bootstrap"):
                if (message.get("kind") != (account["kind"] if account else "Guest")
                        or account and account["kind"] != "ERP" and message.get("user") != account["email"]):
                    sample["semantic_error"] = "unexpected_authenticated_session"
            elif (not isinstance(message.get("assessments"), list)
                    or not isinstance(message.get("counts"), dict)
                    or type(message.get("total")) is not int or message["total"] < 0
                    or message.get("page_size") != 15
                    or len(message["assessments"]) > 15
                    or message["total"] < len(message["assessments"])
                    or any(not isinstance(row, dict) or not isinstance(row.get("name"), str)
                        or not isinstance(row.get("entity"), str) for row in message["assessments"])):
                sample["semantic_error"] = "invalid_dashboard_shape"
        if account and response.history and not protected_api:
            final_path = urlparse(response.url).path
            if account["kind"] != "ERP" or not final_path.startswith(("/app/", "/desk/")):
                sample["semantic_error"] = "unexpected_protected_page_redirect"
        return sample
    except requests.RequestException:
        return {"status": 0, "elapsed_ms": (time.perf_counter() - started) * 1000, "bytes": 0, "queries": None}


def routes(account=None):
    if account is None:
        return ["/grc-site", "/login", "/api/method/ia_maturity.grc.public.site_content"]
    result = [account["home"], "/api/method/ia_maturity.grc.api.bootstrap"]
    if account["kind"] in {"Customer", "Auditor"}:
        result += ["/api/method/ia_maturity.grc.api.dashboard"]
    return result


def probe(base_url, label, repetitions, output):
    path = validate(base_url, output)
    state = json.loads(STATE.read_text())
    result = {"label": label, "base_url": base_url, "scale": state["scale"], "environment": "local isolated Gunicorn lab",
        "started_at": time.time(), "repetitions": repetitions, "roles": {}}
    selected = {"anonymous": None, **{key: account for key, account in state["users"].items() if key == account["role_key"]}}
    for key, account in selected.items():
        client = requests.Session()
        if account:
            client.cookies.update(account["cookies"])
        result["roles"][key] = {}
        for route in routes(account):
            samples = [request(client, base_url + route, account) for _ in range(repetitions)]
            result["roles"][key][route] = {"first_request": samples[0], "summary": summarize(samples), "samples": samples}
        path.write_text(json.dumps(result, indent=2))
        print(json.dumps({"role": key, "routes": {r: v["summary"] for r, v in result["roles"][key].items()}}), flush=True)
    result["finished_at"] = time.time()
    path.write_text(json.dumps(result, indent=2))


def load(base_url, label, duration, ramp, output):
    path = validate(base_url, output)
    state = json.loads(STATE.read_text())
    accounts = list(state["users"].values())
    if len(accounts) != 40:
        raise RuntimeError("Prepare all 40 distinct native-authenticated fixture accounts before a 50-client run.")
    clients = [None] * 10 + accounts
    started = time.monotonic()
    started_epoch = time.time()
    source_before = application_fingerprint()
    steady = started + ramp
    stop = steady + duration
    samples = defaultdict(list)
    lock = threading.Lock()
    resources = []
    previous_cpu = None

    def process_resources():
        result = []
        for pid_file in sorted((ROOT / "diagnostics/performance-20261113").glob("*.pid")):
            try:
                master = int(pid_file.read_text())
                command = Path(f"/proc/{master}/cmdline").read_bytes().replace(b"\0", b" ").decode()
                expected_script = "performance_environment.py" if pid_file.stem.startswith("gunicorn-") else "performance_proxy.py"
                if expected_script not in command or pid_file.stem.rsplit("-", 1)[-1] not in command:
                    continue
                children = [int(p) for p in Path(f"/proc/{master}/task/{master}/children").read_text().split()]
                for pid in [master, *children]:
                    status = Path(f"/proc/{pid}/status").read_text().splitlines()
                    safe = {line.split(":")[0]: line.split(":", 1)[1].strip() for line in status
                        if line.startswith(("VmRSS:", "Threads:"))}
                    stat = Path(f"/proc/{pid}/stat").read_text()
                    fields = stat[stat.rfind(")") + 2:].split()
                    result.append({"group": pid_file.stem, "pid": pid, "master": pid == master,
                        "rss_mb": round(int(safe.get("VmRSS", "0 kB").split()[0]) / 1024, 2),
                        "threads": int(safe.get("Threads", "0")),
                        "cpu_seconds": round((int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"), 3)})
            except (OSError, ValueError, IndexError):
                continue
        return result

    def resource_sample():
        nonlocal previous_cpu
        cpu = list(map(int, Path("/proc/stat").read_text().splitlines()[0].split()[1:9]))
        total, idle = sum(cpu), cpu[3] + cpu[4]
        busy = None
        if previous_cpu and total > previous_cpu[0]:
            busy = round(100 * (1 - (idle - previous_cpu[1]) / (total - previous_cpu[0])), 2)
        previous_cpu = (total, idle)
        memory = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:", "MemAvailable:"))}
        sample = {"elapsed_seconds": round(time.monotonic() - started, 1),
            "sampled_utc": datetime.now(timezone.utc).isoformat(),
            "host_cpu_busy_percent": busy, "host_load_1m": os.getloadavg()[0],
            "memory_available_mb": round(memory["MemAvailable"] / 1024, 1), "processes": process_resources()}
        try:
            import pymysql
            config = guard()
            connection = pymysql.connect(user=config["db_user"], password=config["db_password"],
                unix_socket=config["db_socket"], database=config["db_name"], connect_timeout=2)
            with connection.cursor() as cursor:
                ping_started = time.perf_counter()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                sample["database_ping_ms"] = round((time.perf_counter() - ping_started) * 1000, 3)
                cursor.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_running','Threads_connected','Slow_queries','Questions')")
                sample["database_global"] = {key: int(value) for key, value in cursor.fetchall()}
            connection.close()
            import redis
            common = json.loads((ROOT / "sites/common_site_config.json").read_text())
            cache = redis.Redis.from_url(common.get("redis_cache", "redis://127.0.0.1:13000"), socket_timeout=2)
            ping_started = time.perf_counter()
            cache.ping()
            sample["redis_cache_ping_ms"] = round((time.perf_counter() - ping_started) * 1000, 3)
            cache.close()
        except Exception:
            sample["infrastructure_sample_available"] = False
        resources.append(sample)

    def worker(index, account):
        randomizer = random.Random(index)
        time.sleep(index * ramp / 50)
        client = requests.Session()
        if account:
            client.cookies.update(account["cookies"])
        selected = routes(account)
        cycle = 0
        while time.monotonic() < stop:
            route = selected[cycle % len(selected)]
            sample = request(client, base_url + route, account)
            sample["steady"] = time.monotonic() >= steady
            with lock:
                samples[(account["role_key"] if account else "anonymous", route)].append(sample)
            cycle += 1
            time.sleep(0.8 + randomizer.random() * 0.4)

    def report(final=False):
        resource_sample()
        with lock:
            summary = {role + " " + route: summarize([s for s in items if s["steady"]])
                for (role, route), items in samples.items()}
            total = sum(len(v) for v in samples.values())
        result = {"label": label, "base_url": base_url, "scale": state["scale"],
            "environment": "local isolated Gunicorn lab", "concurrent_clients": 50,
            "distinct_authenticated_accounts": 40, "anonymous_clients": 10, "ramp_seconds": ramp,
            "required_steady_seconds": duration, "elapsed_seconds": round(time.monotonic() - started, 1),
            "total_requests_including_ramp": total, "complete": final, "routes": summary,
            "private_response_cache": False, "external_email": False}
        result["started_utc"] = datetime.fromtimestamp(started_epoch, timezone.utc).isoformat()
        result["planned_steady_start_utc"] = datetime.fromtimestamp(started_epoch + ramp, timezone.utc).isoformat()
        result["planned_workload_stop_utc"] = datetime.fromtimestamp(started_epoch + ramp + duration, timezone.utc).isoformat()
        if final:
            result["completed_utc"] = datetime.now(timezone.utc).isoformat()
        with lock:
            result["errors_including_ramp"] = sum(s["status"] != 200 or bool(s.get("semantic_error"))
                for items in samples.values() for s in items)
            result["steady_requests"] = sum(bool(s["steady"]) for items in samples.values() for s in items)
        result["resource_samples"] = resources
        result["application_source_sha256"] = source_before
        manifest = ROOT / "diagnostics/performance-20261113/final-source-manifest.json"
        if manifest.is_file():
            result["source_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        functional_manifest = ROOT / "diagnostics/performance-20261113/functional-verification-manifest.json"
        if functional_manifest.is_file():
            result["functional_manifest_sha256"] = hashlib.sha256(functional_manifest.read_bytes()).hexdigest()
        if final:
            result["application_source_unchanged"] = source_before == application_fingerprint()
        path.write_text(json.dumps(result, indent=2))
        print(json.dumps({"complete": final, "elapsed_seconds": result["elapsed_seconds"],
            "requests": total, "errors": result["errors_including_ramp"]}), flush=True)
        return result

    resource_sample()
    executor = ThreadPoolExecutor(max_workers=50)
    futures = [executor.submit(worker, index, account) for index, account in enumerate(clients)]
    try:
        while any(not future.done() for future in futures):
            time.sleep(30)
            report()
        for future in futures:
            future.result()
        final_result = report(final=True)
    finally:
        executor.shutdown(wait=True)
    return final_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("probe", "load"))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--duration", type=int, default=1800)
    parser.add_argument("--ramp", type=int, default=60)
    parser.add_argument("--assert-acceptance", action="store_true",
        help="Exit nonzero unless the complete 50-client 30-minute load and source/error/resource gates pass.")
    args = parser.parse_args()
    if args.command == "probe":
        if args.assert_acceptance:
            parser.error("--assert-acceptance is only valid for the complete load command.")
        probe(args.base_url, args.label, args.repetitions, args.output)
    else:
        if args.duration < 60 or args.ramp < 1:
            raise ValueError("Use a positive ramp and at least 60 seconds; acceptance requires 1800 seconds.")
        if args.assert_acceptance and args.duration < 1800:
            parser.error("Acceptance requires at least 1800 steady seconds; use a smoke without this flag.")
        result = load(args.base_url, args.label, args.duration, args.ramp, args.output)
        if args.assert_acceptance:
            from performance_report import load_report
            if not load_report(result)["acceptance_pass"]:
                raise SystemExit("Performance acceptance failed; inspect the retained sanitized report.")


if __name__ == "__main__":
    main()
