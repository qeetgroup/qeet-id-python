"""The concurrency primitives of the synchronous client: a thread lock and a blocking sleep."""

from threading import Lock
from time import sleep

__all__ = ["Lock", "sleep"]
