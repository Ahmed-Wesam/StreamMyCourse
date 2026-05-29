from __future__ import annotations


class HttpError(Exception):
    def __init__(self, status_code: int, message: str, *, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code


class BadRequest(HttpError):
    def __init__(self, message: str, *, code: str | None = "bad_request"):
        super().__init__(400, message, code=code)


class NotFound(HttpError):
    def __init__(self, message: str = "Not found", *, code: str | None = "not_found"):
        super().__init__(404, message, code=code)


class Conflict(HttpError):
    def __init__(self, message: str, *, code: str | None = "conflict"):
        super().__init__(409, message, code=code)


class Unauthorized(HttpError):
    def __init__(self, message: str = "Unauthorized", *, code: str | None = "unauthorized"):
        super().__init__(401, message, code=code)


class Forbidden(HttpError):
    def __init__(self, message: str = "Forbidden", *, code: str | None = "forbidden"):
        super().__init__(403, message, code=code)


class TooManyRequests(HttpError):
    def __init__(
        self,
        message: str = "Too many requests",
        *,
        code: str | None = "rate_limited",
        retry_after_seconds: int | None = None,
    ):
        super().__init__(429, message, code=code)
        self.retry_after_seconds = retry_after_seconds


class RateLimitStoreError(HttpError):
    def __init__(
        self,
        message: str = "Rate limit store unavailable",
        *,
        code: str | None = "rate_limit_store_unavailable",
    ):
        super().__init__(503, message, code=code)


class ServiceUnavailable(HttpError):
    def __init__(self, message: str, *, code: str | None = "service_unavailable"):
        super().__init__(503, message, code=code)

