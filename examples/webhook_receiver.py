"""A webhook receiver on the standard library's WSGI server. Django, Flask and FastAPI work the same way.

QEET_ID_WEBHOOK_SECRET=… python examples/webhook_receiver.py
"""

import os
from collections.abc import Callable, Iterable
from wsgiref.simple_server import make_server

from qeet_id import WebhookVerificationError, construct_webhook_event

SECRETS = [s for s in (os.environ.get("QEET_ID_WEBHOOK_SECRET"), os.environ.get("QEET_ID_WEBHOOK_SECRET_OLD")) if s]
seen: set[str] = set()


def app(environ: dict[str, object], start_response: Callable[..., object]) -> Iterable[bytes]:
    """Verify each delivery, then handle it once."""
    stream = environ["wsgi.input"]
    length = int(str(environ.get("CONTENT_LENGTH") or 0))
    body = stream.read(length) if hasattr(stream, "read") else b""
    headers = {key[5:].replace("_", "-"): str(value) for key, value in environ.items() if key.startswith("HTTP_")}
    try:
        event = construct_webhook_event(body, headers, SECRETS)
    except WebhookVerificationError as error:
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [error.code.encode()]
    if event["id"] not in seen:  # deliveries can repeat: deduplicate on the event's id
        seen.add(event["id"])
        print(event["type"], event["data"])
    start_response("204 No Content", [])
    return []


if __name__ == "__main__":
    with make_server("127.0.0.1", 8080, app) as server:
        server.serve_forever()
