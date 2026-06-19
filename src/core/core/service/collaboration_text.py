from __future__ import annotations

from typing import Any

from models.collaboration import CollabRuntimeChannel, CollabTextDocRuntime


class StoryTextCollabService:
    @staticmethod
    def doc_storage_key(snapshot_id: str, field_name: str) -> str:
        return f"{snapshot_id}:{field_name}"

    @staticmethod
    def selection_storage_key(snapshot_id: str, field_name: str, session_id: str) -> str:
        return f"{snapshot_id}:{field_name}:{session_id}"

    @staticmethod
    def ensure_runtime(channel_state: dict[str, Any]) -> dict[str, Any]:
        runtime = channel_state.get("runtime")
        if isinstance(runtime, dict):
            runtime.setdefault("presence", [])
            runtime.setdefault("locks", [])
            runtime.setdefault("shared_docs", {})
            runtime.setdefault("text_selections", {})
            return runtime

        runtime = {
            "presence": list(channel_state.pop("presence", []) or []),
            "locks": list(channel_state.pop("locks", []) or []),
            "shared_docs": {},
            "text_selections": {},
        }
        raw_shared_docs = channel_state.pop("shared_docs", {}) or {}
        if isinstance(raw_shared_docs, dict):
            for key, item in raw_shared_docs.items():
                runtime["shared_docs"][key] = {**item, "history": item.get("history", []) or []}
        else:
            for item in raw_shared_docs:
                key = StoryTextCollabService.doc_storage_key(item.get("snapshot_id", ""), item.get("field_name", ""))
                runtime["shared_docs"][key] = {**item, "history": item.get("history", []) or []}

        raw_text_selections = channel_state.pop("text_selections", {}) or {}
        if isinstance(raw_text_selections, dict):
            runtime["text_selections"] = dict(raw_text_selections)
        else:
            for item in raw_text_selections:
                key = StoryTextCollabService.selection_storage_key(
                    item.get("snapshot_id", ""),
                    item.get("field_name", ""),
                    item.get("session_id", ""),
                )
                runtime["text_selections"][key] = item
        channel_state["runtime"] = runtime
        return runtime

    @staticmethod
    def export_runtime(channel_state: dict[str, Any]) -> CollabRuntimeChannel:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return CollabRuntimeChannel.model_validate(
            {
                "presence": runtime.get("presence", []),
                "locks": runtime.get("locks", []),
                "shared_docs": list(runtime.get("shared_docs", {}).values()),
                "text_selections": list(runtime.get("text_selections", {}).values()),
            }
        )

    @staticmethod
    def ensure_shared_doc(channel_state: dict[str, Any], snapshot_id: str, field_name: str, text: str = "") -> dict[str, Any]:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        doc_key = StoryTextCollabService.doc_storage_key(snapshot_id, field_name)
        if doc_key not in runtime["shared_docs"]:
            runtime["shared_docs"][doc_key] = CollabTextDocRuntime(
                snapshot_id=snapshot_id,
                field_name=field_name,
                text=text,
            ).model_dump(mode="json")
        return runtime["shared_docs"][doc_key]

    @staticmethod
    def shared_doc(channel_state: dict[str, Any], snapshot_id: str, field_name: str) -> dict[str, Any] | None:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return runtime.get("shared_docs", {}).get(StoryTextCollabService.doc_storage_key(snapshot_id, field_name))

    @staticmethod
    def shared_docs(channel_state: dict[str, Any]) -> dict[str, Any]:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return runtime["shared_docs"]

    @staticmethod
    def text_selections(channel_state: dict[str, Any]) -> dict[str, Any]:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return runtime["text_selections"]

    @staticmethod
    def presence(channel_state: dict[str, Any]) -> list[dict[str, Any]]:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return runtime["presence"]

    @staticmethod
    def locks(channel_state: dict[str, Any]) -> list[dict[str, Any]]:
        runtime = StoryTextCollabService.ensure_runtime(channel_state)
        return runtime["locks"]

    @staticmethod
    def map_position_through_change(position: int, change: dict[str, Any], *, assoc: int) -> int:
        start = int(change.get("from", 0))
        end = int(change.get("to", start))
        insert_length = len(change.get("insert", ""))
        delta = insert_length - (end - start)
        if position < start:
            return position
        if position > end:
            return position + delta
        if position == start == end:
            return position + insert_length if assoc > 0 else position
        if position == start:
            return start if assoc < 0 else start + insert_length
        if position == end:
            return start if assoc < 0 else start + insert_length
        return start if assoc < 0 else start + insert_length

    def rebase_changes(self, changes: list[dict[str, Any]], history: list[dict[str, Any]], version: int) -> list[dict[str, Any]]:
        rebased = [dict(change) for change in changes]
        for entry in history[version:]:
            for applied_change in entry.get("changes", []):
                for index, change in enumerate(rebased):
                    change_start = int(change.get("from", 0))
                    change_end = int(change.get("to", change_start))
                    rebased[index] = {
                        "from": self.map_position_through_change(change_start, applied_change, assoc=-1),
                        "to": self.map_position_through_change(
                            change_end,
                            applied_change,
                            assoc=-1 if change_start == change_end else 1,
                        ),
                        "insert": str(change.get("insert", "")),
                    }
        return rebased

    @staticmethod
    def apply_changes_to_text(text: str, changes: list[dict[str, Any]]) -> str:
        updated = text
        for change in sorted(changes, key=lambda item: (int(item.get("from", 0)), int(item.get("to", 0))), reverse=True):
            start = int(change.get("from", 0))
            end = int(change.get("to", start))
            insert = str(change.get("insert", ""))
            updated = f"{updated[:start]}{insert}{updated[end:]}"
        return updated
