"""Verify Qeet ID access tokens in your own API, locally, against the issuer's signing keys.

::

    from qeet_id.tokens import TokenVerifier

    verifier = TokenVerifier.from_discovery(audience="https://api.brightleaffoods.in")
    claims = verifier.verify(bearer_token)  # raises TokenVerificationError

``AsyncTokenVerifier`` is the same for ``asyncio`` and trio. A token verified
offline stays valid until it expires, even if its session was revoked
meanwhile; where revocation must take effect at once, introspect instead
(``client.oauth.create_token_guard``).
"""

from qeet_id._async._token_verifier import AsyncTokenVerifier
from qeet_id._claims import AccessTokenActor, AccessTokenClaims
from qeet_id._sync._token_verifier import TokenVerifier

__all__ = ["AccessTokenActor", "AccessTokenClaims", "AsyncTokenVerifier", "TokenVerifier"]
