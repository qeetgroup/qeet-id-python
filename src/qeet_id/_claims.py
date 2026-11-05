"""The claim types of an access token; public through :mod:`qeet_id.tokens`."""

from typing import Any, Literal, Required, TypedDict

__all__ = ["AccessTokenActor", "AccessTokenClaims"]


class AccessTokenActor(TypedDict):
    """RFC 8693: the party acting for the subject, on a delegated token."""

    sub: str


class AccessTokenClaims(TypedDict, total=False):
    """The claims of a Qeet ID access token, as the token carries them."""

    iss: Required[str]
    sub: Required[str]
    """The user's ID; a service principal's or agent's on a machine token."""
    aud: Required[str | list[str]]
    """The platform audience, or the RFC 8707 resource the token was issued for."""
    exp: Required[int]
    iat: int
    nbf: int
    jti: str
    user_id: str
    tenant_id: str
    sid: str
    """The session the token belongs to."""
    scope: str
    """Space-separated scopes."""
    actor_type: Literal["service", "agent"] | str
    """``service`` or ``agent`` on a machine token; absent on a person's."""
    agent_id: str
    act: AccessTokenActor
    client_id: str
    """RFC 9068: the application the token was issued to."""
    exchange_depth: int
    """How many token exchanges produced this token."""
    claims: dict[str, Any]
    """Claims an authentication hook added."""
