"""The installed distribution's version, sent in every request's User-Agent."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__: str = version("qeet-id")
except PackageNotFoundError:  # pragma: no cover - only when run from a source tree that isn't installed
    __version__ = "0.0.0"
