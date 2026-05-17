import json
from typing import Any


EventLog = list[dict[str, Any]]


def dumps_session(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)



def loads_session(payload: str | bytes | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload)



def dumps_event_log(events: EventLog) -> str:
    return json.dumps(events, ensure_ascii=False)



def loads_event_log(payload: str | bytes | None) -> EventLog:
    if payload is None:
        return []
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    return json.loads(payload)
