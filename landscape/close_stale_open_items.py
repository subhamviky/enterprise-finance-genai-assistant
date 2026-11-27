"""One-time cleanup of the demonstration landscape's reconciliation open items (GCP-02 Phase B).

    python landscape/close_stale_open_items.py [--tenant acme] [--prefix recon] [--database "(default)"]          # dry run
    python landscape/close_stale_open_items.py --apply                                                          # do it

Every scenario run leaves the settlement of its short payment as an "open item" that reconciliation keeps offering as
a candidate. Until the fix in reconciliation (resolve_with_adjustment consumes the item) nothing ever closed them, so
they piled up, and reconciliation, which compares a line only with the oldest of them, stopped finding the current
run's settlement. This marks the OPEN items of the tenant as MATCHED (the status the model allows; matched_line says
why), so the next scenario run starts from a clean candidate list. It touches nothing else, and a dry run (the
default) only prints what it would change. For a demonstration landscape only: in a real ledger, open items are cash
still expected and are never closed in bulk.

Needs google-cloud-firestore and your own Google credentials (Cloud Shell has both once the venv has the package)."""
import argparse
from datetime import datetime, timezone

from google.cloud import firestore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", default="acme")
    parser.add_argument("--prefix", default="recon")
    parser.add_argument("--database", default="(default)")
    parser.add_argument("--project", default=None)
    parser.add_argument("--apply", action="store_true", help="change the items; without it, only print")
    args = parser.parse_args()
    client = firestore.Client(project=args.project, database=args.database)
    collection = client.collection(f"{args.prefix}_open")
    docs = [d for d in collection.where("tenant", "==", args.tenant).stream() if d.to_dict().get("status") == "OPEN"]
    print(f"{len(docs)} OPEN item(s) of tenant {args.tenant} in {args.prefix}_open")
    for d in docs[:50]:
        row = d.to_dict()
        print(f"  {row.get('settlement_id')}  {row.get('account')}  {row.get('amount')} {row.get('currency')}  "
              f"settled {row.get('settled_at')}")
    if not args.apply:
        print("dry run: nothing changed. Run again with --apply to close them.")
        return 0
    marker = f"cleanup:{datetime.now(timezone.utc):%Y-%m-%d}"
    batch, n = client.batch(), 0
    for d in docs:
        batch.update(d.reference, {"status": "MATCHED", "matched_line": marker, "version": firestore.Increment(1)})
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = client.batch()
    batch.commit()
    print(f"closed {n} item(s), marked {marker!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
