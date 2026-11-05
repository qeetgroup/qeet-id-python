"""Check the built wheel and sdist hold what users need, and nothing they don't.

uv run python scripts/check_wheel.py dist
"""

import sys
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path

REQUIRED = {"qeet_id/__init__.py", "qeet_id/py.typed", "qeet_id/webhooks.py", "qeet_id/types/__init__.py"}
FORBIDDEN_PARTS = ("tests/", "scripts/", ".github/", "__pycache__", ".pyc")
RUNTIME_DEPENDENCIES = {"httpx2", "anyio", "cryptography"}


def check_wheel(wheel: Path) -> list[str]:
    """Problems with ``wheel``; empty when it is good."""
    problems = []
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
    problems += [f"wheel lacks {name}" for name in sorted(REQUIRED - names)]
    problems += [f"wheel ships {name}" for name in sorted(names) if any(p in name for p in FORBIDDEN_PARTS)]
    if not any(name.startswith("qeet_id/_sync/resources/") for name in names):
        problems.append("wheel lacks the generated synchronous resources")
    if metadata["Requires-Python"] != ">=3.11":
        problems.append(f"Requires-Python is {metadata['Requires-Python']!r}")
    requires = {req.split(">")[0].split("<")[0].split("=")[0].strip() for req in metadata.get_all("Requires-Dist", [])}
    if requires != RUNTIME_DEPENDENCIES:
        problems.append(f"runtime dependencies are {sorted(requires)}, expected {sorted(RUNTIME_DEPENDENCIES)}")
    if "License" in metadata or "License-Expression" in metadata:
        problems.append("the licence is the owner's decision and isn't set yet")
    return problems


def check_sdist(sdist: Path) -> list[str]:
    """Problems with ``sdist``; empty when it is good."""
    with tarfile.open(sdist) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
    wanted = {"pyproject.toml", "README.md", "src/qeet_id/__init__.py", "src/qeet_id/py.typed"}
    return [f"sdist lacks {name}" for name in sorted(wanted - names)]


def main() -> int:
    """Check every artifact in the directory given."""
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        print(f"expected one wheel and one sdist in {dist}, found {len(wheels)} and {len(sdists)}", file=sys.stderr)
        return 1
    problems = check_wheel(wheels[0]) + check_sdist(sdists[0])
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"{wheels[0].name} and {sdists[0].name} hold what they should.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
