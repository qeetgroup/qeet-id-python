"""ES256 JWT verification shared by both token verifiers: parsing, keys, signature and claims (ADR-0006)."""

import base64
import binascii
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from qeet_id._claims import AccessTokenClaims
from qeet_id._errors import TokenVerificationError

__all__ = [
    "DEFAULT_LEEWAY",
    "JWKS_CACHE_TTL",
    "JWKS_REFRESH_COOLDOWN",
    "JWKS_TIMEOUT",
    "ParsedToken",
    "check_audiences",
    "check_claims",
    "parse_jwks",
    "parse_token",
    "verify_signature",
]

DEFAULT_LEEWAY: Final = 30.0
"""Seconds of clock difference allowed when checking ``exp``, ``nbf`` and ``iat``."""
JWKS_CACHE_TTL: Final = 300.0
"""How long fetched keys are used before they are fetched again."""
JWKS_REFRESH_COOLDOWN: Final = 30.0
"""An unknown ``kid`` (or an outage) refetches the keys at most this often."""
JWKS_TIMEOUT: Final = 10.0
"""Seconds a JWKS or discovery request may take."""
MAX_TOKEN_LENGTH: Final = 16 * 1024

_SEGMENT = re.compile(r"^[A-Za-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class ParsedToken:
    """A compact JWS whose header passed the checks. Internal."""

    kid: str
    signing_input: bytes
    signature: bytes
    payload: bytes


def _malformed(message: str = "The token is not a JWT.") -> TokenVerificationError:
    return TokenVerificationError("malformed_token", message)


def _b64url(segment: str) -> bytes:
    if not _SEGMENT.match(segment) or len(segment) % 4 == 1:
        raise _malformed()
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError):  # pragma: no cover - the pattern and length checks catch these first
        raise _malformed() from None


def _json_object(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except ValueError:
        raise _malformed() from None
    if not isinstance(value, dict):
        raise _malformed()
    return value


def parse_token(token: object) -> ParsedToken:
    """Split and check a compact JWS: ES256 only, a ``kid``, no ``crit``.

    Raises:
        TokenVerificationError: ``malformed_token``, ``unsupported_algorithm`` or ``unknown_key``.
    """
    if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
        raise _malformed()
    parts = token.split(".")
    if len(parts) != 3:
        raise _malformed()
    header_part, payload_part, signature_part = parts
    header = _json_object(_b64url(header_part))
    if header.get("alg") != "ES256":
        raise TokenVerificationError("unsupported_algorithm", "Only ES256 tokens are accepted.")
    if "crit" in header:
        raise _malformed("The token has critical header parameters this verifier doesn't understand.")
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise TokenVerificationError("unknown_key", "The token names no signing key (kid).")
    signature = _b64url(signature_part)
    if len(signature) != 64:
        raise TokenVerificationError("invalid_signature", "The token's signature is not an ES256 signature.")
    return ParsedToken(
        kid=kid,
        signing_input=f"{header_part}.{payload_part}".encode("ascii"),
        signature=signature,
        payload=_b64url(payload_part),
    )


def verify_signature(key: ec.EllipticCurvePublicKey, token: ParsedToken) -> None:
    """Check the ES256 signature (raw ``r || s``, RFC 7518 §3.4) with ``key``.

    Raises:
        TokenVerificationError: ``invalid_signature``.
    """
    r = int.from_bytes(token.signature[:32], "big")
    s = int.from_bytes(token.signature[32:], "big")
    try:
        key.verify(encode_dss_signature(r, s), token.signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        raise TokenVerificationError("invalid_signature", "The token's signature is not valid.") from None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def check_claims(
    payload: bytes, *, issuer: str, audiences: Sequence[str], leeway: float, now: float
) -> AccessTokenClaims:
    """Check ``exp``, ``nbf``, ``iat``, ``iss``, ``aud`` and ``sub``, and return the claims.

    Raises:
        TokenVerificationError: ``malformed_token``, ``token_expired``, ``token_not_yet_valid``,
            ``invalid_issuer`` or ``invalid_audience``.
    """
    claims = _json_object(payload)
    exp = _number(claims.get("exp"))
    if exp is None:
        raise _malformed("The token has no expiry (exp).")
    if now - leeway >= exp:
        raise TokenVerificationError("token_expired", "The token has expired.")
    nbf = _number(claims.get("nbf"))
    if nbf is not None and now + leeway < nbf:
        raise TokenVerificationError("token_not_yet_valid", "The token is not valid yet (nbf).")
    iat = _number(claims.get("iat"))
    if iat is not None and now + leeway < iat:
        raise TokenVerificationError("token_not_yet_valid", "The token was issued in the future (iat).")
    if claims.get("iss") != issuer:
        raise TokenVerificationError("invalid_issuer", "The token was issued by another issuer.")
    aud = claims.get("aud")
    token_audiences = [aud] if isinstance(aud, str) else aud if isinstance(aud, list) else []
    if not any(isinstance(a, str) and a in audiences for a in token_audiences):
        raise TokenVerificationError("invalid_audience", "The token was not issued for this audience.")
    if not isinstance(claims.get("sub"), str):
        raise _malformed("The token has no subject (sub).")
    return cast("AccessTokenClaims", claims)


def check_audiences(audience: str | Sequence[str]) -> tuple[str, ...]:
    """The audiences a verifier accepts: at least one, each a non-empty string.

    Raises:
        ValueError: without an audience; a token issued for another service would pass.
    """
    audiences = (audience,) if isinstance(audience, str) else tuple(audience)
    if not audiences or any(not isinstance(a, str) or not a for a in audiences):
        raise ValueError("audience is required: without it a token issued for another service would pass.")
    return audiences


def parse_jwks(document: object) -> dict[str, ec.EllipticCurvePublicKey]:
    """The P-256 signing keys of a JWKS document, by ``kid``. Keys that aren't usable are skipped."""
    keys: dict[str, ec.EllipticCurvePublicKey] = {}
    entries = document.get("keys") if isinstance(document, Mapping) else None
    for jwk in entries if isinstance(entries, list) else []:
        if not isinstance(jwk, Mapping) or jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
            continue
        kid, x, y = jwk.get("kid"), jwk.get("x"), jwk.get("y")
        if not (isinstance(kid, str) and kid and isinstance(x, str) and isinstance(y, str)):
            continue
        if jwk.get("use", "sig") != "sig" or jwk.get("alg", "ES256") != "ES256":
            continue
        try:
            x_bytes, y_bytes = _b64url(x), _b64url(y)
            if len(x_bytes) != 32 or len(y_bytes) != 32:
                continue
            numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(x_bytes, "big"), int.from_bytes(y_bytes, "big"), ec.SECP256R1()
            )
            keys[kid] = numbers.public_key()
        except (TokenVerificationError, ValueError):
            continue  # a malformed key is skipped; the others still verify
    return keys
