"""Summarize sanitized local performance artifacts without reading secrets.

This reports lab percentiles and explicit acceptance gates. It never labels
interaction samples as field INP or treats incomplete load runs as acceptance.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from performance_environment import ROOT

EVIDENCE = ROOT / "diagnostics/performance-20261113"


def read(filename):
    path = Path(filename).resolve()
    if not path.is_relative_to(EVIDENCE) or path.suffix != ".json":
        raise ValueError("Read only sanitized JSON evidence in the local performance diagnostics directory.")
    return json.loads(path.read_text())


def raw_percentile(values, fraction):
    values = sorted(v for v in values if v is not None)
    return values[math.ceil(len(values) * fraction) - 1] if values else None


def percentile(values, fraction, precision=3):
    value = raw_percentile(values, fraction)
    return round(value, precision) if value is not None else None


def browser_report(data):
    rows = data["results"]
    groups = []
    for profile, role in sorted({(row["profile"], row["role"]) for row in rows}):
        selected = [r for r in rows if r["profile"] == profile and r["role"] == role]
        result = {"profile": profile, "role": role, "observations": len(selected),
            "p75_lcp_ms": percentile([r["metrics"]["lcp"] for r in selected], .75),
            "p75_cls": percentile([r["metrics"]["cls"] for r in selected], .75, 8),
            "p95_ready_ms": percentile([r["ready_ms"] for r in selected], .95),
            "p95_driver_ready_ms": percentile([r.get("driver_ready_ms") for r in selected], .95),
            "p95_navigation_ms": percentile([r.get("internal_navigation_ms") for r in selected], .95),
            "p95_driver_navigation_ms": percentile([r.get("driver_navigation_ms") for r in selected], .95),
            "interaction_status_counts": dict(Counter(r["metrics"].get("interaction_measurement_status", "legacy_sample_without_count") for r in selected)),
            "p95_observed_interaction_sample_ms": percentile([r["metrics"].get("interaction_sample_max") for r in selected], .95)}
        gates = {"sample_count": len(selected) >= 20,
            "layout": raw_percentile([r["metrics"]["cls"] for r in selected], .75) <= .1}
        gates["font_settlement_proof"] = all(r["metrics"].get("font_settlement", {}).get("fonts_status") == "loaded"
            and (role == "erp" or len(r["metrics"].get("font_settlement", {}).get("links", [])) == 1)
            and all(link.get("outcome") == "loaded" and link.get("sheet_registered")
                for link in r["metrics"].get("font_settlement", {}).get("links", [])) for r in selected)
        if role in {"anonymous", "login"}:
            gates["lcp"] = all(r["metrics"]["lcp"] > 0 for r in selected) and raw_percentile([r["metrics"]["lcp"] for r in selected], .75) <= 2500
        elif role != "erp":
            gates["browser_native_ready_clock"] = all(r.get("ready_clock") == "browser_native_stable_layout" for r in selected)
            gates["dashboard_ready"] = raw_percentile([r["ready_ms"] for r in selected], .95) <= 3000
            navigation = raw_percentile([r.get("internal_navigation_ms") for r in selected], .95)
            gates["navigation"] = navigation is not None and navigation <= 1000
        result["gates"] = gates
        groups.append(result)
    expected_groups = data.get("expected_groups", 24)
    return {"observations": len(rows), "groups": groups, "expected_groups": expected_groups,
        "language": data.get("language", "en"),
        "portal_readiness_method": data.get("portal_readiness_method", "legacy_driver_diagnostic"),
        "font_settlement_method": data.get("font_settlement_method", "legacy_FontFaceSet_only"),
        "acceptance_pass": len(groups) == expected_groups and all(all(g["gates"].values()) for g in groups),
        "field_inp_measured": False, "erp_scope": "native setup screen; ERPNext fixture setup is incomplete"}


def load_report(data):
    routes = data.get("routes", {})
    errors = sum(r["errors"] for r in routes.values())
    resources = data.get("resource_samples", [])
    slowest = max((r["p95_ms"] or 0 for r in routes.values()), default=None)
    semantic = Counter()
    for route in routes.values():
        semantic.update(route.get("semantic_errors", {}))
    return {"complete": data.get("complete", False), "clients": data.get("concurrent_clients"),
        "authenticated_accounts": data.get("distinct_authenticated_accounts"), "anonymous_clients": data.get("anonymous_clients"),
        "steady_seconds_required": data.get("required_steady_seconds"), "elapsed_seconds": data.get("elapsed_seconds"),
        "requests_including_ramp": data.get("total_requests_including_ramp"), "errors": errors,
        "errors_including_ramp": data.get("errors_including_ramp"),
        "steady_requests": data.get("steady_requests"),
        "unexpected_semantic_errors": dict(semantic),
        "redirects": sum(r.get("redirects", 0) for r in routes.values()),
        "max_route_p95_ms": slowest,
        "resource_samples": len(resources), "application_source_unchanged": data.get("application_source_unchanged"),
        "acceptance_pass": bool(data.get("complete") and data.get("concurrent_clients") == 50
            and data.get("required_steady_seconds", 0) >= 1800 and data.get("application_source_unchanged")
            and data.get("elapsed_seconds", 0) >= data.get("required_steady_seconds", 0) + data.get("ramp_seconds", 0)
            and len(resources) >= 61 and routes and not errors
            and not data.get("errors_including_ramp", errors)
            and slowest is not None and slowest <= 3000),
        "scope": "authenticated read workload on isolated local Gunicorn/gzip rehearsal"}


def api_report(before, after):
    rows = []
    for role, paths in before["roles"].items():
        for route, sample in paths.items():
            if not route.endswith("dashboard"):
                continue
            optimized = after["roles"][role][route]
            old = sample["summary"]
            new = optimized["summary"]
            rows.append({"role": role, "baseline_samples": old["samples"], "optimized_samples": new["samples"],
                "baseline_median_ms": old["p50_ms"], "optimized_median_ms": new["p50_ms"],
                "baseline_query_p95": old["p95_sql_queries"], "optimized_query_p95": new["p95_sql_queries"],
                "decoded_payload_sizes_equal": old["p95_bytes"] == new["p95_bytes"],
                "response_hashes_equal": {s.get("semantic_sha256") for s in sample["samples"]}
                    == {s.get("semantic_sha256") for s in optimized["samples"]}})
    return {"rows": rows, "small_baseline_samples_are_diagnostic": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser")
    parser.add_argument("--load")
    parser.add_argument("--baseline-api")
    parser.add_argument("--optimized-api")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = {}
    if args.browser:
        result["browser"] = browser_report(read(args.browser))
    if args.load:
        result["load"] = load_report(read(args.load))
    if args.baseline_api and args.optimized_api:
        result["api"] = api_report(read(args.baseline_api), read(args.optimized_api))
    if args.output:
        path = Path(args.output).resolve()
        if not path.is_relative_to(EVIDENCE) or path.suffix != ".json":
            raise ValueError("Write only sanitized JSON evidence in the local performance diagnostics directory.")
        path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
