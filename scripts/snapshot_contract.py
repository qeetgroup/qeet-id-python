"""Snapshot the API contract the SDK is tested against.

Reads qeet-id-server's five OpenAPI documents and its webhook event catalogue
out of a git ref (without checking it out) and writes what the tests need:

    uv run --with pyyaml python scripts/snapshot_contract.py /path/to/qeet-id-server origin/main

writes tests/contract/openapi.json. For every operation: its method and path,
whether an API key may call it, its query parameters, whether it honours
Idempotency-Key, its request body's content types and fields, and the fields of
its success response.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

DOCUMENTS = ("management", "auth", "federation", "developer", "operations")
METHODS = ("get", "post", "put", "patch", "delete")
OUTPUT = Path(__file__).resolve().parent.parent / "tests" / "contract" / "openapi.json"


def git_show(server: str, ref: str, path: str) -> str:
    """A file's text at ``ref``."""
    return subprocess.run(
        ["git", "-C", server, "show", f"{ref}:{path}"], check=True, capture_output=True, text=True
    ).stdout


def resolve(doc: dict[str, Any], node: Any, depth: int = 0) -> Any:
    """Follow local ``$ref``s."""
    while isinstance(node, dict) and "$ref" in node and depth < 32:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            break
        node = doc
        for part in ref[2:].split("/"):
            node = node[part]
        depth += 1
    return node


def properties(doc: dict[str, Any], schema: Any, depth: int = 0) -> list[str]:
    """The top-level property names of an object schema, following allOf, oneOf and anyOf."""
    schema = resolve(doc, schema)
    if not isinstance(schema, dict) or depth > 8:
        return []
    names = list((schema.get("properties") or {}).keys())
    for key in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(key) or []:
            names += properties(doc, sub, depth + 1)
    return sorted(set(names))


def operations(doc: dict[str, Any], name: str) -> list[dict[str, Any]]:
    """Every operation of one document."""
    out = []
    default_security = doc.get("security")
    for path, raw_item in (doc.get("paths") or {}).items():
        item = resolve(doc, raw_item)
        shared = item.get("parameters") or []
        for method in METHODS:
            op = item.get(method)
            if not op:
                continue
            security = op.get("security", default_security) or []
            schemes = sorted({scheme for requirement in security for scheme in requirement})
            params = [resolve(doc, p) for p in shared + (op.get("parameters") or [])]
            body = resolve(doc, op.get("requestBody")) or {}
            content = body.get("content") or {}
            body_fields = sorted({f for media in content.values() for f in properties(doc, media.get("schema"))})
            response_fields: list[str] = []
            response_status = None
            for status in ("200", "201", "202", "204"):
                response = resolve(doc, (op.get("responses") or {}).get(status))
                if response:
                    response_status = status
                    for media in (response.get("content") or {}).values():
                        response_fields = properties(doc, media.get("schema"))
                        break
                    break
            out.append(
                {
                    "document": name,
                    "method": method.upper(),
                    "path": path,
                    "operation_id": op.get("operationId"),
                    "security": schemes,
                    "query": sorted(p["name"] for p in params if p.get("in") == "query"),
                    "idempotency_key": any(p.get("in") == "header" and p["name"] == "Idempotency-Key" for p in params),
                    "body": {"content_types": sorted(content), "fields": body_fields},
                    "response": {"status": response_status, "fields": response_fields},
                }
            )
    return out


def event_catalogue(events_go: str) -> list[str]:
    """The event names of internal/developer/webhooks/events.go."""
    block = events_go.split("var Events = []EventType{", 1)[1].split("\n}\n", 1)[0]
    return re.findall(r'^\s*\{"([a-z_.]+)",', block, flags=re.MULTILINE)


def main() -> int:
    """Write the snapshot."""
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    server = sys.argv[1]
    ref = sys.argv[2] if len(sys.argv) > 2 else "origin/main"
    commit = subprocess.run(
        ["git", "-C", server, "rev-parse", "--short", ref], check=True, capture_output=True, text=True
    ).stdout.strip()
    ops = []
    for name in DOCUMENTS:
        doc = yaml.safe_load(git_show(server, ref, f"api/openapi/{name}.yaml"))
        ops += operations(doc, name)
    snapshot = {
        "description": "The API contract the SDK is tested against: scripts/snapshot_contract.py over "
        "qeet-id-server's api/openapi/*.yaml and webhook event catalogue. Regenerate it; don't edit it.",
        "source": {"ref": ref, "commit": commit},
        "webhook_events": event_catalogue(git_show(server, ref, "internal/developer/webhooks/events.go")),
        "operations": sorted(ops, key=lambda op: (op["path"], op["method"])),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # One operation per line: small, and a contract change reads as a one-line diff.
    head = {key: value for key, value in snapshot.items() if key != "operations"}
    lines = [json.dumps(op, separators=(",", ":")) for op in snapshot["operations"]]
    text = json.dumps(head, indent=1)[:-2] + ',\n "operations": [\n  ' + ",\n  ".join(lines) + "\n ]\n}\n"
    json.loads(text)
    OUTPUT.write_text(text)
    print(f"Wrote {len(ops)} operations and {len(snapshot['webhook_events'])} events from {ref} ({commit}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
