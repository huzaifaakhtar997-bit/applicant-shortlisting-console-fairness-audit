"""Local versioned model snapshots and append-only audit events."""

import copy
import json
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import joblib


class AuditStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "models").mkdir(exist_ok=True)
        self.db = self.root / "audit.sqlite3"
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def event(self, action, payload):
        item = {
            "id": uuid.uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "payload": payload,
        }
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute(
                "INSERT INTO events VALUES (?,?,?,?)",
                (
                    item["id"],
                    item["created_at"],
                    action,
                    json.dumps(payload, allow_nan=False),
                ),
            )
        return item

    def history(self, limit=100):
        with closing(sqlite3.connect(self.db)) as connection:
            query = (
                "SELECT id,created_at,action,payload FROM events ORDER BY rowid DESC"
            )
            records = connection.execute(
                query if limit is None else query + " LIMIT ?",
                () if limit is None else (limit,),
            ).fetchall()
        return [
            {"id": i, "created_at": t, "action": a, "payload": json.loads(p)}
            for i, t, a, p in records
        ]

    def save_model(self, engine):
        snapshot = copy.copy(engine)
        snapshot.models_comparison_cache = None
        snapshot.dim_cache = None
        destination = self.root / "models" / (engine.version + ".joblib")
        temporary = destination.with_suffix(".tmp")
        joblib.dump(snapshot, temporary, compress=3)
        os.replace(temporary, destination)

    def load_model(self, version):
        if (
            not version
            or len(version) != 12
            or any(c not in "0123456789abcdef" for c in version)
        ):
            raise ValueError("Invalid model version.")
        return joblib.load(self.root / "models" / (version + ".joblib"))

    def save_active(self, version, policy, history):
        destination = self.root / "active.json"
        temp = destination.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "model_version": version,
                    "policy": policy.to_dict(),
                    "version_history": history,
                }
            ),
            encoding="utf-8",
        )
        os.replace(temp, destination)

    def load_active(self):
        file = self.root / "active.json"
        return json.loads(file.read_text(encoding="utf-8")) if file.exists() else None
