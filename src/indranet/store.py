"""Local SQLite artifact history. Database ownership is not a security boundary."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Iterable
from .canon import ContractError, canonical, verify

class Store:
    def __init__(self, filename: str | Path = ":memory:") -> None:
        self.db = sqlite3.connect(str(filename))
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS artifacts (
          ordinal INTEGER PRIMARY KEY AUTOINCREMENT,
          cid TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
          canonical TEXT NOT NULL, envelope TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS by_kind ON artifacts(kind);
        CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON artifacts
          BEGIN SELECT RAISE(ABORT, 'Artifact history is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON artifacts
          BEGIN SELECT RAISE(ABORT, 'Artifact history is append-only'); END;
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def append(self, record: dict) -> str:
        self.append_many([record])
        return record["cid"]

    def append_many(self, records: Iterable[dict]) -> None:
        batch = list(records)
        for record in batch:
            verify(record)
        batch_ids = {record["cid"] for record in batch}
        with self.db:
            for record in batch:
                for parent in record["parents"]:
                    if parent not in batch_ids and not self.has(parent):
                        raise ContractError(f"Unresolved parent: {parent}")
                previous = self.db.execute("SELECT canonical FROM artifacts WHERE cid=?", (record["cid"],)).fetchone()
                if previous and previous[0] != record["canonical"]:
                    raise ContractError("Content identity collision")
                # The first envelope is retained; createdAt is not in the inspected digest body.
                self.db.execute("INSERT OR IGNORE INTO artifacts(cid,kind,canonical,envelope) VALUES(?,?,?,?)",
                    (record["cid"], record["kind"], record["canonical"], canonical(record)))

    def has(self, cid: str) -> bool:
        return self.db.execute("SELECT 1 FROM artifacts WHERE cid=?", (cid,)).fetchone() is not None

    def get(self, cid: str) -> dict:
        result = self.db.execute("SELECT envelope FROM artifacts WHERE cid=?", (cid,)).fetchone()
        if result is None:
            raise KeyError(cid)
        record = json.loads(result[0])
        verify(record)
        return record

    def all(self, kind: str | None = None) -> list[dict]:
        sql = "SELECT envelope FROM artifacts" + (" WHERE kind=?" if kind else "") + " ORDER BY ordinal"
        rows = self.db.execute(sql, (kind,) if kind else ()).fetchall()
        result = [json.loads(row[0]) for row in rows]
        for record in result:
            verify(record)
        return result

    def closure(self, refs: Iterable[str]) -> list[dict]:
        found: dict[str, dict] = {}
        active: set[str] = set()
        def visit(cid: str) -> None:
            if cid in active:
                raise ContractError("Dependency cycle")
            if cid in found:
                return
            active.add(cid)
            record = self.get(cid)
            for parent in record["parents"]:
                visit(parent)
            active.remove(cid)
            found[cid] = record
        for cid in refs:
            visit(cid)
        return list(found.values())
