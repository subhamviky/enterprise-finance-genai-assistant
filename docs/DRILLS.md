# Failure drills on the real cloud (GCP-02 Phase B)

Each drill breaks one thing on purpose, watches what the system does, restores it, and records how long recovery took. They run in Cloud Shell, cost nothing (they stop and start resources that are already running, and use no model), and each ends with a table row to fill in for the evidence. Do them one at a time, on a quiet landscape, and run `landscape-gcp` on `main` first so you start from a known good state.

```bash
PROJECT=finance-ai-landscape-123456; REGION=us-central1; ZONE=$REGION-a
SETTLEMENT=$(gcloud run services describe settlement-service --region $REGION --format='value(status.url)')
health() { curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$SETTLEMENT/actuator/health"; }
```

`health` prints 200 when settlement-service is up. If it prints 401 or 403, your account is not an invoker of the service: add it to `INVOKER_MEMBERS` of the settlement stack, or use the scenario accounts' tokens as the workflow does.

---

## Drill 1: the ledger database VM stops

**What it shows:** settlement-service depends on PostgreSQL on one Always Free VM. With the VM stopped, the service must refuse work, not corrupt or invent anything; after the VM starts, it must recover by itself, with the data intact.

```bash
echo "before: $(health)"                                              # expect 200
gcloud compute instances stop ledger-db --zone $ZONE --quiet
T0=$(date +%s)
sleep 45; echo "VM stopped, health: $(health)"                        # expect not 200 (503/500/timeout)
gcloud compute instances start ledger-db --zone $ZONE --quiet
T1=$(date +%s); echo "VM start accepted after $((T1-T0)) s since the stop"
until [ "$(health)" = "200" ]; do sleep 5; done
echo "RECOVERED: health 200 again $(( $(date +%s) - T1 )) s after the VM start was requested"
```

Then confirm nothing was lost: run `landscape-gcp` on `main`; all 14 steps should still pass, and step 8 balances the ledger.

| Recorded | Value |
|---|---|
| Health while the VM was stopped | |
| Seconds from the start request to health 200 | |
| `landscape-gcp` after recovery | pass / fail |

**Why it recovers by itself:** the database container is a systemd service with `Restart=always` that waits for the password from Secret Manager (retries for up to 10 minutes) before starting; the data is on the VM's persistent disk. Cloud Run's startup probe (`/actuator/health`) keeps new instances out of service until the database answers.

---

## Drill 2: Pub/Sub stops delivering settlement events to audit-ai

**What it shows:** audit-ai receives events by Pub/Sub push. If delivery stops, events must wait in the subscription (retained 24 hours), and when delivery resumes they must be audited exactly once, with no manual repair.

Record the push settings first (the pause removes them; the restore puts them back):

```bash
SUB=audit-settlement-events
ENDPOINT=$(gcloud pubsub subscriptions describe $SUB --format='value(pushConfig.pushEndpoint)')
SA=$(gcloud pubsub subscriptions describe $SUB --format='value(pushConfig.oidcToken.serviceAccountEmail)')
AUD=$(gcloud pubsub subscriptions describe $SUB --format='value(pushConfig.oidcToken.audience)')
echo "$ENDPOINT | $SA | $AUD"          # all three must be non-empty before you go on
```

Break it (the subscription becomes a pull subscription: nothing is pushed):

```bash
gcloud pubsub subscriptions modify-push-config $SUB --push-endpoint=""
```

Now generate events: run `landscape-gcp` on `main` (Run workflow). **Expected: it fails at step 2** (`timed out waiting for … audit-ai`), because no event reaches audit-ai. That failure is the evidence that the drill really broke delivery.

Restore, and time the recovery:

```bash
gcloud pubsub subscriptions modify-push-config $SUB --push-endpoint="$ENDPOINT" \
  --push-auth-service-account="$SA" --push-auth-token-audience="$AUD"
T0=$(date +%s)
until gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="audit-ai-service" AND httpRequest.requestMethod="POST" AND httpRequest.status=204' \
      --freshness=5m --limit=1 --format='value(timestamp)' | grep -q .; do sleep 5; done
echo "FIRST EVENT DELIVERED $(( $(date +%s) - T0 )) s after the restore"
```

Then run `landscape-gcp` again: it must pass (a redelivered event adds no second finding: step 9b).

| Recorded | Value |
|---|---|
| Step of the failed run | step 2 |
| Seconds from the restore to the first delivered event | |
| Second `landscape-gcp` run | pass / fail |

If the dead-letter queue received anything (`gcloud pubsub subscriptions pull audit-settlement-events-dlq --limit=3`, no `--auto-ack`), note it: after `max_delivery_attempts` (5) a message goes there, which does not happen here because the subscription is paused, not failing.

---

## Drill 3: restore the ledger from its backup

**What it shows:** the daily `pg_dump` in Cloud Storage can actually be restored. A backup that was never restored is not a backup. The drill restores into a scratch database and never touches the live one.

The database VM can **write** backups but not read them (`roles/storage.objectCreator` only, on purpose: a compromised database host cannot read or delete its own backups). So the restore is done by you: download the dump in Cloud Shell, check it is a whole gzip, and stream it into the VM over IAP.

```bash
PROJECT=finance-ai-landscape-123456; ZONE=us-central1-a; BUCKET=$PROJECT-ledger-backups
VM="gcloud compute ssh ledger-db --zone $ZONE --tunnel-through-iap --command"
$VM 'sudo systemctl start ledger-backup.service; sleep 5; sudo systemctl is-failed ledger-backup.service || true'   # inactive = it ran and finished
LATEST=$(gcloud storage ls gs://$BUCKET | sort | tail -1 | sed "s#gs://$BUCKET/##"); echo "restoring $LATEST"
gcloud storage cp gs://$BUCKET/$LATEST /tmp/ledger.sql.gz && ls -l /tmp/ledger.sql.gz
gunzip -t /tmp/ledger.sql.gz && echo "the dump is a whole, valid gzip"
time {
  $VM "sudo docker exec ledger-db psql -U settlement -d postgres -c 'drop database if exists restore_test' -c 'create database restore_test'"
  gunzip -c /tmp/ledger.sql.gz | $VM "sudo docker exec -i ledger-db psql -q -U settlement -d restore_test >/dev/null"
  $VM "echo live:     \$(sudo docker exec ledger-db psql -At -U settlement -d settlement -c 'select count(*) from settlement') settlements; echo restored: \$(sudo docker exec ledger-db psql -At -U settlement -d restore_test -c 'select count(*) from settlement') settlements"
  $VM "sudo docker exec ledger-db psql -U settlement -d postgres -c 'drop database restore_test'"
}
rm -f /tmp/ledger.sql.gz
```

The two counts should be equal (or the restored one smaller only by settlements made after that backup ran).

| Recorded | Value |
|---|---|
| Backup object and size | |
| `gunzip -t` | valid / not |
| Settlements live / restored | |
| Seconds for the restore | |

**What the first attempt taught (27 November 2026):** run from the VM, the restore failed with `gzip: unexpected end of file` and an empty scratch database. The cause was not the backup: the VM's account cannot read the bucket (by design), the download got a 403 that `curl -sf` hid, and `gunzip` was handed nothing. A drill that fails for a reason of its own design is still useful: it proved the write-only backup account, and the drill now restores the way an operator would.

---

## Not yet automated: redeploy during an approval

A proposal waits for a second person; its state lives in Firestore, not in the service. The claim is that a new revision of the assistant, deployed while a proposal waits, loses nothing: the approval can still be decided and posts once. The scenario cannot show this on its own (it runs start to finish in two minutes); it needs the scenario split in two halves around a redeploy. That is the next piece of Phase B.
