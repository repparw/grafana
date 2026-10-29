# Grafana Cloud dashboards

This repository contains dashboard resources for the Grafana Cloud Git Sync integration at `https://repparw.grafana.net`.

- `dashboards/` is the synced path. Keep `metadata.name` stable to preserve dashboard UIDs and links.
- `connection.json` and `repository.json` document the Git Sync integration, but are outside the synced path.
- Cloud owns alert rules, contact points and notification policy; these are backed up privately by Epsilon through encrypted Restic backups rather than committed here.
- GitHub App credentials and live service tokens remain SOPS-encrypted in [repparw/nix](https://github.com/repparw/nix).
- Dashboard edits from Cloud should be proposed as pull requests; merges to `main` are picked up by the existing Git Sync connection after it has been switched to this repository.

## Cutover

Do **not** enable a second repository syncing the same dashboard UIDs in parallel.
Update existing `fleet-dashboards` repository in Grafana Cloud to use `https://github.com/repparw/grafana`, branch `main`, path `dashboards/`, preserving the existing `fleet-github` connection and branch workflow. Verify dashboard UID `fleet-overview` and live alert counts before removing the old dashboard copy in `repparw/nix`.
