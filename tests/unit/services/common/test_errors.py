from __future__ import annotations

import pytest

from services.common.errors import BadRequest, Conflict, HttpError, NotFound


class TestHttpError:
    def test_carries_status_message_and_optional_code(self) -> None:
        err = HttpError(418, "I'm a teapot", code="teapot")
        assert err.status_code == 418
        assert err.message == "I'm a teapot"
        assert err.code == "teapot"
        assert str(err) == "I'm a teapot"

    def test_code_is_optional(self) -> None:
        err = HttpError(500, "boom")
        assert err.code is None


class TestBadRequest:
    def test_defaults(self) -> None:
        err = BadRequest("missing field")
        assert err.status_code == 400
        assert err.message == "missing field"
        assert err.code == "bad_request"

    def test_custom_code(self) -> None:
        assert BadRequest("x", code="malformed").code == "malformed"

    def test_subclasses_http_error(self) -> None:
        with pytest.raises(HttpError):
            raise BadRequest("nope")


class TestNotFound:
    def test_defaults(self) -> None:
        err = NotFound()
        assert err.status_code == 404
        assert err.message == "Not found"
        assert err.code == "not_found"

    def test_custom_message_and_code(self) -> None:
        err = NotFound("Lesson not found", code="lesson_missing")
        assert err.message == "Lesson not found"
        assert err.code == "lesson_missing"

    def test_subclasses_http_error(self) -> None:
        with pytest.raises(HttpError):
            raise NotFound()


class TestConflict:
    def test_defaults(self) -> None:
        err = Conflict("already exists")
        assert err.status_code == 409
        assert err.message == "already exists"
        assert err.code == "conflict"

    def test_subclasses_http_error(self) -> None:
        with pytest.raises(HttpError):
            raise Conflict("clash")
