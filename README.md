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
the prior archive rather than replacing it with an incomplete one.

**Verify export completeness separately from Restic service status.** A snapshot
may upload successfully even when the Grafana export failed. Check the
`grafana-cloud-state` entry in
`/var/lib/backup-exports/offsite.json`, the Grafana export journal, and the
archive's modification time:

```sh
sudo python3 -m json.tool /var/lib/backup-exports/offsite.json
sudo journalctl -u grafana-cloud-backup.service -n 50 --no-pager
sudo stat -c '%y %n' /var/lib/grafana-cloud-backup/grafana-cloud-state.tar.gz
```

Confirm the latest report marks the Grafana export complete and the archive was
refreshed for that run. A successful Restic upload alone is insufficient.

**Treat exports as secrets.** Never commit them or webhook URLs to Git. The
export is a sequence of API reads, not an atomic snapshot; avoid editing Cloud
settings during an export. It excludes metrics/log history, datasource secrets,
organization users/RBAC and GitHub App credentials. Keep the App recovery key
and backup token in [Nix SOPS](https://github.com/repparw/nix), not here.
The backup token expires **2027-10-26** and must be rotated beforehand.

## Restore configuration

**Full restoration has not been round-trip tested.** The archive's hashes have
been verified, but restore fidelity—including permissions, contact-point
secrets, alert behavior and notification delivery—has not been demonstrated.
The tested `gcx` v1.7.1 export was incomplete and redacted contact-point
secrets, so it is not a drop-in replacement or a verified one-command restore.

Recovery currently requires an ordered, manual procedure. Work from a private
Restic-restored archive:

1. Verify file hashes against `manifest.json`. Do not expose decrypted contact
   point settings in logs or public files.
2. Recreate the `fleet-github` Git Sync connection separately using the
   GitHub App key from Nix SOPS. Reattach `fleet-dashboards` to this repository
   without creating a second owner for the same dashboard. Restore folders,
   folder permissions and dashboards through Git Sync or native APIs while
   preserving UIDs. Verify dashboard permissions independently.
3. Recover datasource credentials separately; `datasources.json` is metadata
   only. Organization users and RBAC also require separate recovery.
4. Restore alert rules from `alert-rules-api.json` with the provisioning API,
   using `X-Disable-Provenance: true` where UI editing should remain possible.
   Export-format files and provisioning API request bodies are **different**.
5. Restore contact points, templates, mute timings and finally notification
   policies. The `contact-points.json` file is an export-format document:
   convert it to the API's expected payload shape before restoring. Ensure
   decrypted settings are present; **never treat redacted secrets as recovered
   credentials**. Keep alert evaluation paused until destinations and queries
   have been checked.
6. Verify dashboard queries, datasource connectivity, alert-rule counts,
   permissions and actual notification delivery before resuming the intended
   rules.

Test recovery on disposable resources rather than overwriting live alerting.
Until a complete round-trip is proven, do not describe this archive as a
verified one-command restore.
