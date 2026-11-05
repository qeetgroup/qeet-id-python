"""Generate the synchronous client from the asynchronous one.

``src/qeet_id/_async`` is the source of truth. Each of its modules, except the
hand-written ones listed in ``HAND_WRITTEN``, becomes the module of the same
path under ``src/qeet_id/_sync``: ``async``/``await`` removed, ``Async*`` names
renamed, ``qeet_id._async`` imports pointed at ``qeet_id._sync``. The output
is then sorted and formatted with Ruff.

    uv run python scripts/unasync.py          # regenerate src/qeet_id/_sync
    uv run python scripts/unasync.py --check  # fail when it is out of date (CI)
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "qeet_id" / "_async"
TARGET = ROOT / "src" / "qeet_id" / "_sync"

HAND_WRITTEN = {Path("__init__.py"), Path("_compat.py"), Path("_resource.py")}
"""Modules that differ in more than syntax, kept by hand in both trees."""

HEADER = "# Generated from qeet_id/_async/{path} by scripts/unasync.py. Edit that file, not this one.\n"

SUBSTITUTIONS: list[tuple[str, str]] = [
    (r"\bqeet_id\._async\b", "qeet_id._sync"),
    (r"\bAsyncPaginator\b", "Page"),
    (r"\bAsyncPage\b", "Page"),
    (r"\bAsyncIterator\b", "Iterator"),
    (r"\bAsyncIterable\b", "Iterable"),
    (r"\bStopAsyncIteration\b", "StopIteration"),
    (r"\b__aenter__\b", "__enter__"),
    (r"\b__aexit__\b", "__exit__"),
    (r"\b__aiter__\b", "__iter__"),
    (r"\b__anext__\b", "__next__"),
    (r"\baclose\b", "close"),
    (r"\bAsync([A-Z]\w*)", r"\1"),
    (r"\basync def\b", "def"),
    (r"\basync with\b", "with"),
    (r"\basync for\b", "for"),
    (r"\bawait ", ""),
    (r"\basynchronous\b", "synchronous"),
    (r"\bAn synchronous\b", "A synchronous"),
    (r"\ban synchronous\b", "a synchronous"),
]


def unasync(text: str) -> str:
    """Rewrite one module of the asynchronous client as its synchronous twin."""
    for pattern, replacement in SUBSTITUTIONS:
        text = re.sub(pattern, replacement, text)
    return text


def sources() -> list[Path]:
    """The generated modules' paths, relative to the trees' roots."""
    return sorted(
        path.relative_to(SOURCE) for path in SOURCE.rglob("*.py") if path.relative_to(SOURCE) not in HAND_WRITTEN
    )


def generate(into: Path) -> list[Path]:
    """Write every generated module under ``into``, sorted and formatted."""
    written = []
    for relative in sources():
        target = into / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(HEADER.format(path=relative.as_posix()) + unasync((SOURCE / relative).read_text()))
        written.append(target)
    if written:
        config = ["--config", str(ROOT / "pyproject.toml")]
        files = [str(path) for path in written]
        subprocess.run(["ruff", "check", "--quiet", "--fix", "--select", "I,RUF022", *config, *files], check=True)
        subprocess.run(["ruff", "format", "--quiet", *config, *files], check=True)
    return written


def generated_in(tree: Path) -> set[Path]:
    """The generated modules present in ``tree``."""
    return {path.relative_to(tree) for path in tree.rglob("*.py") if path.relative_to(tree) not in HAND_WRITTEN}


def main() -> int:
    """Regenerate the synchronous tree, or check that it is up to date."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail when src/qeet_id/_sync is out of date")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as scratch:
        fresh = Path(scratch) / "_sync"
        generate(fresh)
        expected = generated_in(fresh)
        present = generated_in(TARGET)
        if args.check:
            stale = sorted(
                path
                for path in expected | present
                if path not in expected
                or path not in present
                or (fresh / path).read_text() != (TARGET / path).read_text()
            )
            if stale:
                print("src/qeet_id/_sync is out of date; run: uv run python scripts/unasync.py", file=sys.stderr)
                for path in stale:
                    print(f"  {path.as_posix()}", file=sys.stderr)
                return 1
            print(f"src/qeet_id/_sync is up to date ({len(expected)} generated modules).")
            return 0
        for path in present - expected:
            (TARGET / path).unlink()
        for path in expected:
            (TARGET / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fresh / path, TARGET / path)
        print(f"Generated {len(expected)} modules in src/qeet_id/_sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
