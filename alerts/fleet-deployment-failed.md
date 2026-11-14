# Fleet deployment failure alert

**Rule title:** `fleet_cloud_deployment_failed`  
**Scope:** The fleet deployment controller, currently Pi.  
**Owner:** Grafana Cloud Alerting. This file documents the alert; the Git Sync
connection only manages `dashboards/`, not alert rules.

## Signal

`repparw/nix` exports these metrics from the controller through the existing
Alloy textfile collector:

- `fleet_deployment_last_attempt_status`: `2` while a full-fleet deploy
  is running, `0` after failure, `1` after deploy-rs returns success.
- `fleet_deployment_last_attempt_timestamp_seconds`: last state transition,
  derived from the atomic status file's modification time.

They come from `/var/lib/auto-update/last-attempt-status`, which survives
reboots. Only the host owning `fleet-deploy.service` publishes these series,
so the query follows the controller without hardcoding `host="pi"`. Missing metrics before the first deployment are expected. Selective
host deployments do not change the full-fleet result. An interrupted full-fleet
deployment retains state `2` until a subsequent full-fleet attempt.

## Alert definition

Create a Grafana-managed alert using the existing Prometheus-compatible fleet
metrics datasource, in the existing fleet health alert folder and group.

PromQL query A (instant):

```promql
(fleet_deployment_last_attempt_status == bool 0)
+
on(host)
(
  (fleet_deployment_last_attempt_status == bool 2)
  *
  on(host)
  (
    (time() - fleet_deployment_last_attempt_timestamp_seconds)
      > bool 14400
  )
)
```

- Alert condition: A is above `0.5`. This fires for a recorded failure or
  a run still marked as running after four hours. The fleet timer's transient
  job is bounded at 180 minutes, so normal deployments do not trigger the
  second condition.
- Evaluation interval: at most five minutes. Pending period: two minutes.
- Severity/routing: reuse the existing fleet health alert policy and
  `Grafana Cloud Alerts` Discord contact point, no new contact point.
- No Data / Error: **Keep Last State**. Collection staleness and metrics
  datasource availability have separate alerts.
- Summary: `Fleet deployment failed or stalled on {{ $labels.host }}`.
- Description: `Inspect journalctl -u fleet-deploy-run on Pi, then review
  /var/lib/auto-update/last-attempted-revision and last-attempt-status.
  Do not blindly retry while a remote activation might still be running.`

## Verification

1. After deploying the Nix change, check that the next full-fleet attempt
   generates both metrics in Grafana Explore, labeled with the controller host.
   State `1` is healthy; `0` is failure; `2` is running.
2. Create or update this exact rule in Grafana Cloud (this Markdown document
   is not automatically synchronized). Preview query A with the live metric.
3. Verify the alert instance, notification policy, and recovery route.
   Use a disposable test rule or provisioned fixture instead of deliberately
   failing a live fleet deployment.
4. Confirm that a successful full-fleet retry clears the failure signal.
   A selective host retry leaves the full-fleet result unchanged.
5. Back up the Cloud rule through the existing encrypted Grafana export.

**Completion criterion:** The live rule exists, is enabled, evaluates
correctly, and routes through the existing Discord contact point. Merging
this documentation alone does not meet that criterion.
