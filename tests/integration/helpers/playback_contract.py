"""Shared playback contract assertions for integration tests."""

from __future__ import annotations


def assert_playback_contract(body: dict) -> None:
    provider = body.get("provider")
    if provider == "s3":
        url = body.get("playbackUrl")
        assert isinstance(url, str) and url, f"Expected non-empty playbackUrl: {body}"
        return
    if provider == "kinescope":
        assert isinstance(body.get("videoId"), str) and body["videoId"]
        assert isinstance(body.get("drmAuthToken"), str) and body["drmAuthToken"]
        return
    raise AssertionError(f"Unexpected playback provider payload: {body}")
