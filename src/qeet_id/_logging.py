"""The SDK's logger.

Messages carry the method, path, attempt, status, duration and request ID;
never credentials, headers, query strings or bodies.
"""

import logging

__all__ = ["logger"]

logger = logging.getLogger("qeet_id")
logger.addHandler(logging.NullHandler())
