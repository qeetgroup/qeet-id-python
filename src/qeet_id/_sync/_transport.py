# Generated from qeet_id/_async/_transport.py by scripts/unasync.py. Edit that file, not this one.
"""Executes requests: credentials, headers, body, timeouts, typed errors, and retries where safe."""

import json
import time
from typing import TYPE_CHECKING, Any

import httpx2

from qeet_id._config import check_headers, check_max_retries, check_timeout
from qeet_id._errors import APIError, NetworkError, QeetIDError, RequestTimeoutError, error_from_response
from qeet_id._logging import logger
from qeet_id._options import RequestOptions
from qeet_id._request import (
    QueryPairs,
    Request,
    basic_authorization,
    check_idempotency_key,
    encode_body,
    encode_query,
    new_idempotency_key,
)
from qeet_id._retry import SAFE_METHODS, is_retryable, retry_delay
from qeet_id._sync._compat import sleep

if TYPE_CHECKING:
    from qeet_id._sync._credentials import Credential

__all__ = ["Transport"]


class Transport:
    """Sends requests to the API for one client. Safe for concurrent use. Internal."""

    __slots__ = ("_credential", "_headers", "_http", "_owns_http", "base_url", "max_retries", "timeout", "user_agent")

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float | httpx2.Timeout,
        max_retries: int,
        headers: dict[str, str],
        user_agent: str,
        credential: "Credential | None",
        http_client: httpx2.Client | None,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self._headers = headers
        self._credential = credential
        self._owns_http = http_client is None
        # Redirects are never followed: Authorization must not leave the API's origin.
        self._http = http_client if http_client is not None else httpx2.Client(follow_redirects=False)

    def request(
        self,
        request: Request,
        *,
        idempotency_key: str | None = None,
        request_options: RequestOptions | None = None,
    ) -> Any:
        """Send ``request``, retrying where safe, and return the decoded JSON body (``None`` when empty)."""
        options: RequestOptions = request_options or {}
        headers = {
            **self._headers,
            **check_headers(options.get("headers"), name="request_options['headers']"),
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if request.idempotent:
            key = new_idempotency_key() if idempotency_key is None else check_idempotency_key(idempotency_key)
            headers["Idempotency-Key"] = key
        elif idempotency_key is not None:
            raise TypeError("This call doesn't accept an idempotency_key: the API doesn't make it idempotent.")
        content, content_type = encode_body(request)
        if content_type is not None:
            headers["Content-Type"] = content_type
        if request.client_auth is not None:
            headers["Authorization"] = basic_authorization(*request.client_auth)

        timeout = options.get("timeout", self.timeout)
        check_timeout(timeout, name="request_options['timeout']")
        max_retries = check_max_retries(
            options.get("max_retries", self.max_retries), name="request_options['max_retries']"
        )
        if not request.retries:
            max_retries = 0
        retry_safe = request.retry_safe or request.method in SAFE_METHODS or "Idempotency-Key" in headers
        url = self.base_url + request.path
        params = encode_query(request.query)

        attempt = 0
        while True:
            # Outside the retry: a credential that can't be got isn't a transient failure of this request.
            authorization = self._authorization(request)
            try:
                return self._attempt(
                    request,
                    url=url,
                    params=params,
                    headers=headers,
                    authorization=authorization,
                    content=content,
                    attempt_timeout=timeout,
                    attempt=attempt,
                )
            except (APIError, NetworkError) as error:
                delay = None
                if attempt < max_retries and is_retryable(error, retry_safe=retry_safe):
                    delay = retry_delay(attempt, error)
                if delay is None:
                    raise
                logger.info(
                    "qeet_id: retrying %s %s in %.2f s after %s (attempt %d)",
                    request.method,
                    request.path,
                    delay,
                    _describe(error),
                    attempt + 1,
                )
                sleep(delay)
                attempt += 1

    def _authorization(self, request: Request) -> str | None:
        if not request.authenticate or request.client_auth is not None:
            return None
        if self._credential is None:
            raise QeetIDError(
                "This call needs credentials: give the client an api_key, or a client_id and client_secret.",
                code="missing_credentials",
            )
        return self._credential.authorization(self)

    def _attempt(
        self,
        request: Request,
        *,
        url: str,
        params: QueryPairs,
        headers: dict[str, str],
        authorization: str | None,
        content: bytes | None,
        attempt_timeout: float | httpx2.Timeout,
        attempt: int,
    ) -> Any:
        if authorization is not None:
            headers = {**headers, "Authorization": authorization}
        started = time.monotonic()
        try:
            response = self._http.request(
                request.method,
                url,
                params=params or None,
                headers=headers,
                content=content,
                timeout=attempt_timeout,
            )
        except httpx2.TimeoutException as exc:
            raise RequestTimeoutError(
                f"{request.method} {request.path} got no response in time ({type(exc).__name__})."
            ) from exc
        except httpx2.HTTPError as exc:
            raise NetworkError(
                f"{request.method} {request.path} could not reach the Qeet ID API: {type(exc).__name__}: {exc}"
            ) from exc

        status = response.status_code
        logger.debug(
            "qeet_id: %s %s -> %d in %.0f ms (attempt %d, request %s)",
            request.method,
            request.path,
            status,
            (time.monotonic() - started) * 1000,
            attempt + 1,
            response.headers.get("x-request-id", "-"),
        )
        if not 200 <= status < 300:
            if status == 401 and authorization is not None and self._credential is not None:
                self._credential.invalidate(authorization)
            raise error_from_response(status, response.headers, response.content)
        if status == 204 or not response.content:
            return None
        try:
            return json.loads(response.content)
        except ValueError:
            raise APIError(
                "The API answered with a body that is not JSON.",
                status=status,
                code="invalid_response",
                request_id=response.headers.get("x-request-id"),
                headers=response.headers,
            ) from None

    def close(self) -> None:
        """Close the HTTP client, unless the caller passed their own."""
        if self._owns_http:
            self._http.close()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.base_url!r})"


def _describe(error: QeetIDError) -> str:
    if isinstance(error, APIError):
        return f"{error.status} {error.code}"
    return error.code
