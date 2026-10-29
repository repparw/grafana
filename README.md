# Grafana Cloud dashboards

This repository contains dashboard resources for the Grafana Cloud Git Sync integration at `https://repparw.grafana.net`.

- `dashboards/` is the synced path. Keep `metadata.name` stable to preserve dashboard UIDs and links.
- `connection.json` and `repository.json` document the Git Sync integration, but are outside the synced path.
- Cloud owns alert rules, contact points and notification policy; these are backed up privately by Epsilon through encrypted Restic backups rather than committed here.
- GitHub App credentials and live service tokens remain SOPS-encrypted in [repparw/nix](https://github.com/repparw/nix).
- Dashboard edits from Cloud should be proposed as pull requests; merges to `main` are picked up by the existing Git Sync connection after it has been switched to this repository.

## Validation

`tests/dashboard_queries.py` reads the actual Git-synced dashboard and builds Prometheus query regression cases covering missing telemetry, CPU usage, filtered network interfaces, filesystem calculations and failed services. The dashboard workflow runs these using `promtool test rules` on pushes and pull requests. Host-side Alloy/monitoring tests remain in `repparw/nix`.
