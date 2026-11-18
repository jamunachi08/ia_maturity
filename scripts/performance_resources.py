"""Read-only database latency companion for the isolated performance lab.

Never emits credentials or SQL text. Watches an existing sanitized load report,
sampling SELECT 1 until the report is complete. No app requests or writes.
"""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import time

import pymysql

from performance_environment import ROOT, guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evidence = ROOT / "diagnostics/performance-20261113"
    source, output = Path(args.load).resolve(), Path(args.output).resolve()
    if any(not p.is_relative_to(evidence) or p.suffix != ".json" for p in (source, output)) or source == output:
        raise ValueError("Use separate sanitized JSON artifacts in the local diagnostics directory.")
    config = guard()
    result = {"scope": "read-only SELECT1 RTT; companion begins during steady state, not at ramp start", "samples": []}
    while True:
        load = json.loads(source.read_text())
        sample = {"sampled_utc": datetime.now(timezone.utc).isoformat(),
            "latest_load_elapsed_seconds": load["elapsed_seconds"], "load_complete": load.get("complete", False)}
        try:
            with pymysql.connect(user=config["db_user"], password=config["db_password"],
                    unix_socket=config["db_socket"], database=config["db_name"], connect_timeout=2) as connection:
                with connection.cursor() as cursor:
                    started = time.perf_counter()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    sample["database_ping_ms"] = round((time.perf_counter() - started) * 1000, 3)
        except Exception:
            sample["sample_available"] = False
        result["samples"].append(sample)
        result["complete"] = load.get("complete", False)
        output.write_text(json.dumps(result, indent=2))
        if result["complete"]:
            break
        time.sleep(30)


if __name__ == "__main__":
    main()
