"""Accept Qeet ID access tokens in your own API: verify them locally, then check a scope.

python examples/protect_an_api.py eyJhbGciOiJFUzI1NiIs…
"""

import sys

from qeet_id import TokenVerificationError, TokenVerifier

verifier = TokenVerifier.from_discovery(audience="https://api.brightleaffoods.in")


def authorize(bearer_token: str, scope: str) -> str:
    """Return the caller's user ID, or raise PermissionError."""
    try:
        claims = verifier.verify(bearer_token)
    except TokenVerificationError as error:
        raise PermissionError(f"401: {error.code}") from error
    if scope not in claims.get("scope", "").split():
        raise PermissionError(f"403: the token lacks {scope}")
    return claims["sub"]


if __name__ == "__main__":
    print(authorize(sys.argv[1], "invoices:read"))
