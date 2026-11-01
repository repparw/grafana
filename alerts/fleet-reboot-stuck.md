# Headless fleet reboot stuck alert

**Rule title:** `fleet_cloud_reboot_stuck`  
**Scope:** Pi and Epsilon only. Alpha has a separate manual-reboot policy.  
**Owner:** Grafana Cloud Alerting; this repository's Git Sync manages only
`dashboards/` and **does not deploy this rule**.

## Definition

Create a **Grafana-managed, multi-dimensional alert** using the existing
Prometheus-compatible fleet metrics datasource. Verify the datasource and
notification policy against the existing `Reboot required` alert before saving.

- PromQL query A (instant):
  ```promql
  max by (host) (fleet_reboot_required{host=~"pi|epsilon"})
  ```
- Alert condition: each series in A is **above 0.5** (the collector reports
  `1` when a reboot is pending, `0` when the staged and booted kernel,
  initrd and modules agree). Keep `host` as the alert instance dimension;
  do not reduce across hosts.
- Pending period (`for`): **26h continuously pending**.
- Evaluation: reuse the existing fleet health alert group if it evaluates at
  least every 5m, or create a 5m group in the same alert folder.
- Severity and routing: match the existing fleet health/reboot policy that
  delivers warnings through `Grafana Cloud Alerts` to Discord. Do not
  introduce a new contact point or override the notification policy.
- No Data / Error: **Keep Last State**, consistent with ordinary fleet health
  alerts. The separate collection-staleness and Cloud query-availability alerts
  handle missing samples and datasource faults.
- Suggested summary: `{{ $labels.host }} still needs a reboot after 26h`.
- Suggested description: `The host's staged kernel/initrd/modules have differed from the running boot for more than 26h. Check fleet debug and the headless reboot service on Pi before any manual reboot.`

The 03:00 headless reboot timer is the fallback for busy backups, manual staging,
or a skipped post-deployment trigger. This alert reports a **persistent pending
reboot**, not a failure to deploy a particular commit.

## One-time Cloud activation

1. In Grafana Cloud, check whether `fleet_cloud_reboot_stuck` already exists.
   Update it rather than creating a duplicate.
2. In Explore, verify `fleet_reboot_required{host=~"pi|epsilon"}` returns both
   host labels, with values `0` or `1`. Confirm the collector freshness
   monitor covers missing samples.
3. Create or update the alert using the rule above. Preview the query and
   threshold, inspect the per-host instances, and verify the notification
   route. Save the rule in Cloud.
4. Confirm its evaluation is healthy and that the rule appears in Alerting.
   Test notification delivery using Grafana's notification test or a disposable
   test rule rather than deliberately leaving a production host pending.
5. Run and verify the scheduled private `grafana-cloud-backup.service` export
   on Epsilon. Its archive contains alert rules; **never commit it** to Git.

**Completion criterion:** The live rule is present, enabled, evaluating, and
routed correctly in Grafana Cloud. Merging this document does **not** meet
that criterion.

## Live host prerequisite

Before enabling automatic headless reboots, follow the real Pi/Epsilon boot
link checks in
[the fleet operations runbook](https://github.com/repparw/nix/blob/main/docs/runbooks/fleet-operations.md).
CI's fake boot links prove script behavior, not the hosts' actual layout.
