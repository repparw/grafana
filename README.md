# Grafana Cloud

Cloud stack: [repparw.grafana.net](https://repparw.grafana.net).

This repository versions dashboards edited in the Grafana Cloud UI. Fleet-side
Alloy collection, credentials and automated backups live in [repparw/nix](https://github.com/repparw/nix);
see its [monitoring runbook](https://github.com/repparw/nix/blob/main/docs/runbooks/monitoring.md).

## Dashboard Git Sync

The existing Grafana Cloud repository `fleet-dashboards` uses:

- **GitHub:** `repparw/grafana`, branch `main`, path `dashboards/`, folderless target
- **Connection:** `fleet-github` GitHub App
- **Workflow:** pull requests; polling every five minutes, webhooks disabled

Edit dashboards in the Cloud UI, review the resulting GitHub PR, and merge to
`main`. Keep `metadata.name` and dashboard UIDs stable (the fleet dashboard is
`fleet-overview`). After changes, check sync status and panel behavior.

The synced files are in [dashboards/](dashboards/). [connection.json](connection.json)
and [repository.json](repository.json) document the integration but live outside
the synced path; they are not automatically applied to Cloud. Do not configure
another repository to manage the same dashboard UID.

**Git Sync does not cover this stack's alerts, contact points, notification
policies or templates.** Those are edited directly in Cloud and backed up
privately as described below.

## Alerts and notifications

Cloud owns the alert rules and notification configuration; editing them does
not require a NixOS deployment.

- Keep ordinary health alerts at **Keep Last State** for query errors and No Data.
  The separate **Cloud metrics query availability** alert reports datasource
  failures instead of treating them as host or disk failures.
- The **Grafana Cloud Alerts** contact point sends Discord notifications.
  Preview firing, recovery and mixed-severity notifications after template edits.
  Recovery is a separate message, not deletion of the original.
- Use `fleet_failed_unit` for failed-unit alerts, with a zero-valued
  host baseline from `fleet_health_collection_timestamp_seconds`. This allows
  the last failed unit to resolve; collector-staleness alerts handle missing facts.
- Alpha may be intentionally offline, so its absence needs its own uptime policy.
  After changing scrape targets or labels, check active-series usage in
  `grafanacloud-usage`. Disk thresholds are configured in
  [Nix](https://github.com/repparw/nix/blob/main/modules/aspects/monitoring-health.nix).

## Automated private backup

Epsilon's [`grafana-cloud-backup.service`](https://github.com/repparw/nix/blob/main/modules/aspects/monitoring-cloud-state.nix)
exports Cloud configuration before its scheduled encrypted offsite Restic backup.
There is no separate Grafana backup timer.

To run the export and offsite backup manually on Epsilon:

```sh
sudo systemctl start --wait restic-backups-offsite.service
```

For a local export without an offsite upload:

```sh
sudo systemctl start --wait grafana-cloud-backup.service
```

The archive is
`/var/lib/grafana-cloud-backup/grafana-cloud-state.tar.gz`.
It includes dashboards, folders and permissions, alert rules, contact points
**with decrypted secrets**, notification policies/templates, mute timings and
datasource metadata. Restic retains previous versions. Export failures preserve
the prior archive and mark the offsite run incomplete.

**Treat exports as secrets.** Never commit them or webhook URLs to Git. The
export is a sequence of API reads, not an atomic snapshot; avoid editing Cloud
settings during an export. It excludes metrics/log history, datasource secrets,
organization users/RBAC and GitHub App credentials. Keep the App recovery key
and backup token in [Nix SOPS](https://github.com/repparw/nix), not here.
The backup token expires **2027-10-26** and must be rotated beforehand.

## Restore configuration

A full restore is currently a *manual, ordered recovery procedure*, not a
single tested command. Work from a private Restic-restored archive:

1. Verify file hashes against `manifest.json`. Do not expose decrypted contact
   point settings in logs or public files.
2. Restore folders and their permissions, then dashboards through Git Sync or
   Grafana's dashboard API. Preserve UIDs. Recover datasource credentials
   separately; `datasources.json` contains only metadata.
3. Restore alert rules from `alert-rules-api.json` with the provisioning API.
   Use `X-Disable-Provenance: true` for UI-editable rules. The separately exported
   provisioning-format resources are **not** interchangeable with API payloads.
4. Restore contact points, notification templates, mute timings, and finally
   notification policies. Keep alert evaluation paused until destinations and
   queries have been checked.
5. Verify dashboard queries, datasource connectivity, alert-rule counts and
   actual notification delivery before resuming the intended rules.

Recreate private GitHub App credentials from Nix SOPS when needed; never commit
the private key. Test recovery on disposable resources rather than overwriting
live alerting just to exercise the process.
