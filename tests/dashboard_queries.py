#!/usr/bin/env python3
"""Build promtool cases from the live Git Sync dashboard (formerly tested in nix)."""

import json
from pathlib import Path


def series(metric, labels, values):
    rendered = ",".join(f'{key}="{value}"' for key, value in labels.items())
    return {"series": f"{metric}{{{rendered}}}", "values": values}


def check(expr, expected, at="6m"):
    return {
        "expr": expr,
        "eval_time": at,
        "exp_samples": [
            {"labels": f'{{host="{host}"}}', "value": value}
            for host, value in expected.items()
        ],
    }


def case(input_series, checks):
    return {"interval": "1m", "input_series": input_series, "promql_expr_test": checks}


def main():
    root = Path(__file__).resolve().parents[1]
    resource = json.loads((root / "dashboards/fleet-overview.json").read_text())
    if resource["metadata"]["name"] != "fleet-overview" or resource["spec"]["uid"] != "fleet-overview":
        raise ValueError("The fleet-overview dashboard UID changed")
    panels = {p["id"]: p for p in resource["spec"]["panels"]}
    required = {1, 3, 4, 5, 6, 7}
    if not required.issubset(panels):
        raise ValueError(f"Missing required dashboard panels: {required - panels.keys()}")

    def expr(panel_id, target=0):
        return panels[panel_id]["targets"][target]["expr"]

    tests = []
    hosts = ["alpha", "pi", "epsilon"]
    for missing in ["none", *hosts]:
        inputs = [
            series("node_uname_info", {"host": host}, "1+0x10")
            for host in hosts
            if host != missing
        ]
        checks = [
            check(expr(7, index), {host: int(host == missing)})
            for index, host in enumerate(hosts)
        ]
        tests.append(case(inputs, checks))

    tests.append(
        case(
            [series("node_uname_info", {"host": "alpha"}, "1+0x3 stale")],
            [check(expr(7), {"alpha": 0}, "4m"), check(expr(7), {"alpha": 1}, "10m")],
        )
    )

    cpu_hosts = [
        ("pi", 1, 65),
        ("alpha", 30, 30),
        ("epsilon", 0, 60),
        ("saturated", 60, 0),
    ]
    cpu_series = [
        series(
            "node_cpu_seconds_total",
            {"host": host, "cpu": "0", "job": "integrations/unix", "mode": mode},
            f"0+{value}x10",
        )
        for host, user, idle in cpu_hosts
        for mode, value in [("user", user), ("idle", idle)]
    ]
    cpu_series.append(
        series(
            "node_cpu_seconds_total",
            {"host": "pi", "cpu": "0", "job": "unrelated", "mode": "user"},
            "0+6000x10",
        )
    )
    tests.append(
        case(
            cpu_series,
            [check(expr(1), {"pi": 100 / 66, "alpha": 50, "epsilon": 0, "saturated": 100})],
        )
    )

    network_series = [
        series(
            f"node_network_{direction}_bytes_total",
            {"host": "alpha", "device": device},
            "0+60x10" if device == "enp6s0" else "0+6000x10",
        )
        for direction in ["receive", "transmit"]
        for device in ["enp6s0", "lo", "veth-fixture", "ifb-wan", "wg-home", "br0"]
    ]
    tests.append(case(network_series, [check(expr(p), {"alpha": 1}) for p in [4, 5]]))

    filesystem_series = [
        series(
            f"node_filesystem_{metric}_bytes",
            {"host": "epsilon", "device": "/dev/sda1", "fstype": "ext4", "mountpoint": mount},
            "1000+0x10" if metric == "size" else "500+0x10" if metric == "free" else "450+0x10",
        )
        for mount in ["/persist", "/nix", "/home/repparw"]
        for metric in ["size", "free", "avail"]
    ]
    tests.append(case(filesystem_series, [check(expr(3), {"epsilon": 100 * 500 / 950})]))

    failures_series = [
        series("fleet_failed_unit", {"host": "alpha", "name": "first.service"}, "1+0x10"),
        series("fleet_failed_unit", {"host": "alpha", "name": "second.service"}, "1+0x10"),
        series("fleet_health_collection_timestamp_seconds", {"host": "alpha", "collector": "host"}, "100+0x10"),
        series("fleet_health_collection_timestamp_seconds", {"host": "epsilon", "collector": "host"}, "100+0x10"),
        series("fleet_failed_units", {"host": "legacy", "job": "integrations/unix"}, "2+0x10"),
        series("node_systemd_unit_state", {"host": "alpha", "name": "test.service", "state": "failed"}, "0+0x10"),
        series("node_systemd_unit_state", {"host": "pi", "name": "test.service", "state": "failed"}, "1+0x10"),
    ]
    tests.append(
        case(
            failures_series,
            [check(expr(6), {"alpha": 2, "pi": 1, "epsilon": 0, "legacy": 2})],
        )
    )
    print(json.dumps({"evaluation_interval": "1m", "fuzzy_compare": True, "tests": tests}, indent=2))


if __name__ == "__main__":
    main()
