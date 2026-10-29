"""Causal immutable message/event exports from the coordinator transaction domain."""
from __future__ import annotations
from .contracts import canonical, digest, identifier, seal, verify
from .global_store import Conflict


class Audit:
    def __init__(self, store): self.store = store

    def message(self, value):
        identifier(value["id"])
        if not isinstance(value.get("text"), str) or not value["text"].strip() or len(value["text"]) > 50000:
            raise ValueError("Bounded public message text required")
        record = seal({**value, "actor_assurance": "poc_anonymous"})
        with self.store.transaction() as db:
            old = db.execute("SELECT body FROM messages WHERE id=?", (value["id"],)).fetchone()
            if old:
                if old[0] != canonical(record): raise Conflict("Message text is immutable; append a superseding message")
                return record
            parent = value.get("in_reply_to")
            if parent:
                identifier(parent)
                existing = self.store._row(db, "messages", "id", parent)
                if verify(__import__('json').loads(existing["body"]))["project_id"] != value["project_id"]:
                    raise Conflict("Reply must remain in its declared project")
            db.execute("INSERT INTO messages VALUES (?,?,?)", (value["id"], parent, canonical(record)))
            self.store._event(db, "message_accepted", record)
        return record

    def messages(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000: raise ValueError("Bounded message page required")
        import json
        with self.store.transaction(write=False) as db:
            return [json.loads(r[0]) for r in db.execute("SELECT body FROM messages ORDER BY rowid DESC LIMIT ?", (limit,))]

    def export_events(self, after=0):
        records = self.store.events(after, limit=1000)
        previous = digest({"after": after})
        items = []
        for event in records:
            entry = seal({"event": event, "previous_sha256": previous})
            items.append(entry); previous = entry["sha256"]
        return seal({"id": "events-" + str(after), "after": after, "items": items, "anchor": previous})

    @staticmethod
    def verify_segment(segment):
        body = verify(segment); previous = digest({"after": body["after"]})
        for item in body["items"]:
            entry = verify(item)
            if entry["previous_sha256"] != previous: raise ValueError("Audit chain differs from retained anchor")
            previous = item["sha256"]
        if previous != body["anchor"]: raise ValueError("Audit segment anchor differs")
        return body
