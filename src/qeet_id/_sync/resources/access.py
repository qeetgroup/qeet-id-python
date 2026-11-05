# Generated from qeet_id/_async/resources/access.py by scripts/unasync.py. Edit that file, not this one.
"""Access: who may do what, and how people sign in (auth.yaml)."""

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Unpack

from qeet_id._options import RequestOptions
from qeet_id._pagination import ListResult, Page
from qeet_id._request import path
from qeet_id._sync._resource import APIResource
from qeet_id.types.access import (
    Anomaly,
    AnomalySummary,
    AuthPolicy,
    AuthPolicyUpdateParams,
    AuthPolicyUsage,
    AuthzenAction,
    AuthzenEntity,
    BotActivity,
    BotSettings,
    DecisionLogEntry,
    DecisionSource,
    EffectivePermissions,
    Evaluation,
    EvaluationRequest,
    Evaluations,
    EvaluationsOptions,
    IPRule,
    IPRuleCheck,
    IPRuleEnforcement,
    IPRuleList,
    Permission,
    PermissionDecision,
    RelationDecision,
    RelationGraph,
    RelationObject,
    RelationObjectType,
    RelationTuple,
    RiskSettings,
    RiskSettingsUpdateParams,
    Role,
    RoleHolders,
    SecurityPolicy,
    SecurityPolicyUpdateParams,
)

__all__ = [
    "AuthPolicies",
    "Decisions",
    "IPRules",
    "Permissions",
    "Relationships",
    "Roles",
    "SecurityPolicies",
    "ThreatDetection",
]


def _without_none(**fields: Any) -> dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


class Roles(APIResource):
    """Roles, the permissions they grant, and who holds them."""

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> ListResult[Role]:
        """List the organisation's roles, built-in and custom."""
        return self._list(path("/v1/tenants/{}/roles", tenant_id), request_options=request_options)

    def create(
        self,
        tenant_id: str,
        /,
        name: str,
        *,
        description: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Role:
        """Create a custom role with no permissions; grant them with ``grant_permission`` or ``set_permissions``."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/roles", tenant_id),
            json=_without_none(name=name, description=description),
            request_options=request_options,
        )

    def update(
        self,
        tenant_id: str,
        role_id: str,
        /,
        *,
        name: str | None = None,
        description: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Role:
        """Rename a custom role or change its description."""
        return self._request(
            "PATCH",
            path("/v1/tenants/{}/roles/{}", tenant_id, role_id),
            json=_without_none(name=name, description=description),
            request_options=request_options,
        )

    def delete(self, tenant_id: str, role_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        """Delete a custom role. Refused with 409 ``rbac.role_in_use`` while anyone holds it."""
        self._request("DELETE", path("/v1/tenants/{}/roles/{}", tenant_id, role_id), request_options=request_options)

    def list_permissions(
        self, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[Permission]:
        """List the permissions the role grants."""
        return self._list(path("/v1/roles/{}/permissions", role_id), request_options=request_options)

    def set_permissions(
        self,
        tenant_id: str,
        role_id: str,
        /,
        permission_ids: Sequence[str],
        *,
        request_options: RequestOptions | None = None,
    ) -> ListResult[Permission]:
        """Make ``permission_ids`` the whole of a custom role's permissions, in one step, and return them."""
        body = self._request(
            "PUT",
            path("/v1/tenants/{}/roles/{}/permissions", tenant_id, role_id),
            json={"permission_ids": [*permission_ids]},
            request_options=request_options,
        )
        return ListResult.from_response(body)

    def grant_permission(
        self, role_id: str, permission_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Grant one permission to a role. Granting it twice changes nothing."""
        self._request(
            "POST", path("/v1/roles/{}/permissions/{}", role_id, permission_id), request_options=request_options
        )

    def revoke_permission(
        self, role_id: str, permission_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        self._request(
            "DELETE", path("/v1/roles/{}/permissions/{}", role_id, permission_id), request_options=request_options
        )

    def list_holders(
        self,
        tenant_id: str,
        role_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> RoleHolders:
        """One page of the people holding the role, and every group granted it."""
        return self._request(
            "GET",
            path("/v1/tenants/{}/roles/{}/holders", tenant_id, role_id),
            query={"limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def assign(
        self, tenant_id: str, user_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Assign a role to a user in the organisation. Assigning it twice changes nothing."""
        self._request(
            "POST",
            path("/v1/users/{}/tenants/{}/roles/{}", user_id, tenant_id, role_id),
            request_options=request_options,
        )

    def unassign(
        self, tenant_id: str, user_id: str, role_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Remove a directly assigned role from a user. A group may still grant it."""
        self._request(
            "DELETE",
            path("/v1/users/{}/tenants/{}/roles/{}", user_id, tenant_id, role_id),
            request_options=request_options,
        )


class Permissions(APIResource):
    """Permission checks and the permission catalogue."""

    def list(self, *, request_options: RequestOptions | None = None) -> ListResult[Permission]:
        """The platform's permission catalogue."""
        return self._list("/v1/permissions", request_options=request_options)

    def check(
        self, *, user_id: str, tenant_id: str, permission: str, request_options: RequestOptions | None = None
    ) -> bool:
        """Whether the user may use the permission: roles and attribute policies composed (a deny wins)."""
        decision = self._request(
            "GET",
            "/v1/check",
            query={"user_id": user_id, "tenant_id": tenant_id, "permission": permission},
            request_options=request_options,
        )
        return isinstance(decision, dict) and decision.get("allowed") is True

    def explain(
        self, *, user_id: str, tenant_id: str, permission: str, request_options: RequestOptions | None = None
    ) -> PermissionDecision:
        """``check`` with its reasons: the deciding model and rule, and the grants or the reason for a deny."""
        return self._request(
            "GET",
            "/v1/check",
            query={"user_id": user_id, "tenant_id": tenant_id, "permission": permission, "explain": True},
            request_options=request_options,
        )

    def list_effective(
        self, tenant_id: str, user_id: str, /, *, request_options: RequestOptions | None = None
    ) -> EffectivePermissions:
        """Every permission the user holds in the organisation, directly or through groups."""
        body = self._request(
            "GET", path("/v1/users/{}/tenants/{}/permissions", user_id, tenant_id), request_options=request_options
        )
        body = body if isinstance(body, dict) else {}
        return {"permissions": body.get("permissions") or [], "grants": body.get("grants") or []}


class Relationships(APIResource):
    """Relationship tuples (ReBAC) and relationship checks."""

    def create(
        self,
        tenant_id: str,
        /,
        *,
        object: str,
        relation: str,
        subject: str,
        request_options: RequestOptions | None = None,
    ) -> RelationTuple:
        """Write a tuple: ``subject`` holds ``relation`` on ``object``."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/relation-tuples", tenant_id),
            json={"object": object, "relation": relation, "subject": subject},
            request_options=request_options,
        )

    def list(
        self,
        tenant_id: str,
        /,
        *,
        object: str | None = None,
        subject: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> ListResult[RelationTuple]:
        """List the tuples on an object (who has what on it) or of a subject (what it reaches). Give one.

        Raises:
            ValueError: unless exactly one of ``object`` and ``subject`` is given.
        """
        if (object is None) == (subject is None):
            raise ValueError("Give exactly one of object and subject.")
        return self._list(
            path("/v1/tenants/{}/relation-tuples", tenant_id),
            {"object": object, "subject": subject},
            request_options=request_options,
        )

    def delete(self, tenant_id: str, tuple_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request(
            "DELETE", path("/v1/tenants/{}/relation-tuples/{}", tenant_id, tuple_id), request_options=request_options
        )

    def check(
        self,
        tenant_id: str,
        /,
        *,
        object: str,
        relation: str,
        user_id: str,
        request_options: RequestOptions | None = None,
    ) -> bool:
        """Whether the user holds the relation on the object, following usersets."""
        decision = self._check(tenant_id, object, relation, user_id, explain=False, options=request_options)
        return decision.get("allowed") is True

    def explain(
        self,
        tenant_id: str,
        /,
        *,
        object: str,
        relation: str,
        user_id: str,
        request_options: RequestOptions | None = None,
    ) -> RelationDecision:
        """``check`` with its reasons: the deciding model and the path of tuples."""
        return self._check(tenant_id, object, relation, user_id, explain=True, options=request_options)

    def _check(
        self, tenant_id: str, obj: str, relation: str, user_id: str, *, explain: bool, options: RequestOptions | None
    ) -> RelationDecision:
        return self._request(
            "POST",
            path("/v1/tenants/{}/relation-tuples/check", tenant_id),
            query={"explain": True if explain else None},
            json={"object": obj, "relation": relation, "user_id": user_id},
            retry_safe=True,
            request_options=options,
        )

    def graph(
        self,
        tenant_id: str,
        /,
        *,
        object: str,
        relation: str,
        depth: int | None = None,
        request_options: RequestOptions | None = None,
    ) -> RelationGraph:
        """The graph of identities reachable from an object and relation, up to ``depth`` hops (1 to 10)."""
        return self._request(
            "GET",
            path("/v1/tenants/{}/relation-tuples/graph", tenant_id),
            query={"object": object, "relation": relation, "depth": depth},
            request_options=request_options,
        )

    def list_types(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> ListResult[RelationObjectType]:
        """The object types the tuples name, with counts."""
        return self._list(path("/v1/tenants/{}/relation-tuples/types", tenant_id), request_options=request_options)

    def list_objects(
        self,
        tenant_id: str,
        /,
        *,
        type: str,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Page[RelationObject]:
        """The objects of one type the tuples name, a page at a time."""
        return self._paginate(
            path("/v1/tenants/{}/relation-tuples/objects", tenant_id),
            {"type": type, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )


class Decisions(APIResource):
    """OpenID AuthZEN evaluations over every authorization model, and the log of decisions made."""

    def evaluate(
        self,
        tenant_id: str,
        /,
        *,
        subject: AuthzenEntity,
        action: AuthzenAction,
        resource: AuthzenEntity | None = None,
        context: Mapping[str, Any] | None = None,
        request_options: RequestOptions | None = None,
    ) -> Evaluation:
        """Evaluate one AuthZEN request.

        With ``resource["type"]`` ``"permission"``, ``action["name"]`` is a permission key;
        otherwise the resource is ``type:id`` and ``action["name"]`` a relation.
        """
        return self._request(
            "POST",
            path("/v1/tenants/{}/access/v1/evaluation", tenant_id),
            json=_without_none(subject=subject, resource=resource, action=action, context=context),
            retry_safe=True,
            request_options=request_options,
        )

    def evaluate_many(
        self,
        tenant_id: str,
        /,
        evaluations: Sequence[EvaluationRequest],
        *,
        subject: AuthzenEntity | None = None,
        resource: AuthzenEntity | None = None,
        action: AuthzenAction | None = None,
        context: Mapping[str, Any] | None = None,
        options: EvaluationsOptions | None = None,
        request_options: RequestOptions | None = None,
    ) -> Evaluations:
        """Evaluate several AuthZEN requests; decisions come back in request order.

        ``subject``, ``resource``, ``action`` and ``context`` are defaults each evaluation may replace.
        """
        body = self._request(
            "POST",
            path("/v1/tenants/{}/access/v1/evaluations", tenant_id),
            json=_without_none(
                subject=subject,
                resource=resource,
                action=action,
                context=context,
                evaluations=[*evaluations],
                options=options,
            ),
            retry_safe=True,
            request_options=request_options,
        )
        return {"evaluations": (body.get("evaluations") if isinstance(body, dict) else None) or []}

    def list(
        self,
        tenant_id: str,
        /,
        *,
        subject: str | None = None,
        source: DecisionSource | None = None,
        allowed: bool | None = None,
        days: int | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Page[DecisionLogEntry]:
        """The access decisions the organisation asked for, newest first, ``days`` back."""
        return self._paginate(
            path("/v1/tenants/{}/authorization/decisions", tenant_id),
            {"subject": subject, "source": source, "allowed": allowed, "days": days, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )


class AuthPolicies(APIResource):
    """The organisation's sign-in policy: methods, password rules and lockout."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AuthPolicy:
        return self._request("GET", path("/v1/tenants/{}/auth-policy", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **policy: Unpack[AuthPolicyUpdateParams],
    ) -> AuthPolicy:
        """Replace the policy. Read it first and send it back whole."""
        return self._request(
            "PUT", path("/v1/tenants/{}/auth-policy", tenant_id), json=policy, request_options=request_options
        )

    def get_usage(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> AuthPolicyUsage:
        """How the organisation's people sign in: who would be locked out by turning a method off."""
        return self._request(
            "GET", path("/v1/tenants/{}/auth-policy/usage", tenant_id), request_options=request_options
        )


class SecurityPolicies(APIResource):
    """The organisation's security policy. Which addresses may sign in is ``ip_rules``."""

    def get(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> SecurityPolicy:
        """The policy, or the platform defaults when none is saved."""
        return self._request("GET", path("/v1/tenants/{}/policy", tenant_id), request_options=request_options)

    def update(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **params: Unpack[SecurityPolicyUpdateParams],
    ) -> SecurityPolicy:
        """Change only the fields given."""
        return self._request(
            "PATCH", path("/v1/tenants/{}/policy", tenant_id), json=params, request_options=request_options
        )

    def replace(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **policy: Unpack[SecurityPolicyUpdateParams],
    ) -> SecurityPolicy:
        """Replace the whole policy."""
        return self._request(
            "PUT", path("/v1/tenants/{}/policy", tenant_id), json=policy, request_options=request_options
        )


class IPRules(APIResource):
    """The organisation's address rules: which networks may sign in."""

    def list(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> IPRuleList:
        body = self._request("GET", path("/v1/tenants/{}/ip-rules", tenant_id), request_options=request_options)
        body = body if isinstance(body, dict) else {}
        return {"enabled": body.get("enabled") is True, "data": body.get("items") or []}

    def create(
        self,
        tenant_id: str,
        /,
        *,
        action: Literal["allow", "deny"],
        cidr: str,
        label: str,
        request_options: RequestOptions | None = None,
    ) -> IPRule:
        """Add a rule for an address range, such as ``203.0.113.0/24``. Deny wins over allow."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/ip-rules", tenant_id),
            json={"action": action, "cidr": cidr, "label": label},
            request_options=request_options,
        )

    def delete(self, tenant_id: str, rule_id: str, /, *, request_options: RequestOptions | None = None) -> None:
        self._request("DELETE", path("/v1/tenants/{}/ip-rules/{}", tenant_id, rule_id), request_options=request_options)

    def check(self, tenant_id: str, /, ip: str, *, request_options: RequestOptions | None = None) -> IPRuleCheck:
        """What the rules make of ``ip``: the decision a sign-in gets. Changes nothing."""
        return self._request(
            "POST",
            path("/v1/tenants/{}/ip-rules/check", tenant_id),
            json={"ip": ip},
            retry_safe=True,
            request_options=request_options,
        )

    def set_enforcement(
        self, tenant_id: str, /, enabled: bool, *, request_options: RequestOptions | None = None
    ) -> IPRuleEnforcement:
        """Turn enforcement of the rules on or off."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/ip-rules/config", tenant_id),
            json={"enabled": enabled},
            request_options=request_options,
        )


class ThreatDetection(APIResource):
    """Bot detection, adaptive-risk settings and sign-in anomalies."""

    def get_bot_activity(
        self,
        tenant_id: str,
        /,
        *,
        verdict: Literal["allowed", "challenged", "blocked"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> BotActivity:
        """Recent bot-detection verdicts and statistics, a page at a time."""
        return self._request(
            "GET",
            path("/v1/tenants/{}/security/bots", tenant_id),
            query={"verdict": verdict, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def get_bot_settings(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> BotSettings:
        return self._request(
            "GET", path("/v1/tenants/{}/security/bots/settings", tenant_id), request_options=request_options
        )

    def update_bot_settings(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None, **settings: Unpack[BotSettings]
    ) -> BotSettings:
        """Replace the bot-detection settings."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/security/bots/settings", tenant_id),
            json=settings,
            request_options=request_options,
        )

    def get_risk_settings(self, tenant_id: str, /, *, request_options: RequestOptions | None = None) -> RiskSettings:
        return self._request(
            "GET", path("/v1/tenants/{}/security/risk-settings", tenant_id), request_options=request_options
        )

    def update_risk_settings(
        self,
        tenant_id: str,
        /,
        *,
        request_options: RequestOptions | None = None,
        **settings: Unpack[RiskSettingsUpdateParams],
    ) -> RiskSettings:
        """Replace the risk settings."""
        return self._request(
            "PUT",
            path("/v1/tenants/{}/security/risk-settings", tenant_id),
            json=settings,
            request_options=request_options,
        )

    def list_anomalies(
        self,
        tenant_id: str,
        /,
        *,
        status: Literal["open", "resolved"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Page[Anomaly]:
        """List sign-in anomalies, newest first."""
        return self._paginate(
            path("/v1/tenants/{}/security/anomalies", tenant_id),
            {"status": status, "limit": limit, "cursor": cursor},
            request_options=request_options,
        )

    def get_anomaly_summary(
        self, tenant_id: str, /, *, request_options: RequestOptions | None = None
    ) -> AnomalySummary:
        return self._request(
            "GET", path("/v1/tenants/{}/security/anomalies/summary", tenant_id), request_options=request_options
        )

    def resolve_anomaly(
        self, tenant_id: str, anomaly_id: str, /, *, request_options: RequestOptions | None = None
    ) -> None:
        """Mark an anomaly reviewed. It blocks or revokes nothing by itself."""
        self._request(
            "POST",
            path("/v1/tenants/{}/security/anomalies/{}/resolve", tenant_id, anomaly_id),
            request_options=request_options,
        )
