"""Where this service keeps its state: E2A's ports, chosen by GENAI_STATE_BACKEND.

  memory     (default) E2A's in-memory reference adapters: tests, local runs, one instance
  firestore  e2a-adapters' Firestore adapters: durable and shared by every Cloud Run instance, in the
             landscape's one free database, collection GENAI_FIRESTORE_COLLECTION (default "genai")

GOOGLE_CLOUD_PROJECT and FIRESTORE_DATABASE (default "(default)") select the database;
FIRESTORE_EMULATOR_HOST points the client at the emulator."""
import os
from typing import Mapping, Tuple

from e2a import BaseIdempotencyStore, BaseTransactionalStore
from e2a_inmemory_adapters import InMemoryIdempotencyStore, InMemoryTransactionalStore


def state_ports(env: Mapping[str, str] = None) -> Tuple[BaseTransactionalStore, BaseIdempotencyStore]:
    """(rows, claims): the store behind approvals and receipts, and the store behind request claims."""
    env = os.environ if env is None else env
    backend = env.get("GENAI_STATE_BACKEND", "memory")
    if backend == "memory":
        return InMemoryTransactionalStore(), InMemoryIdempotencyStore()
    if backend != "firestore":
        raise ValueError(f"GENAI_STATE_BACKEND={backend!r}: use 'memory' or 'firestore'")
    from google.cloud import firestore
    from e2a_adapters.gcp import FirestoreIdempotencyStore, FirestoreTransactionalStore
    client = firestore.Client(project=env.get("GOOGLE_CLOUD_PROJECT"),
                              database=env.get("FIRESTORE_DATABASE", "(default)"))
    collection = env.get("GENAI_FIRESTORE_COLLECTION", "genai")
    return FirestoreTransactionalStore(client, collection), FirestoreIdempotencyStore(client, collection)
