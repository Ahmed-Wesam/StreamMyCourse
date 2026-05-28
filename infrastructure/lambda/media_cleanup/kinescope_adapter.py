from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class KinescopeDeleteAdapter:
    def __init__(self, api_token: str) -> None:
        self._api_token = (api_token or "").strip()

    def delete_video(self, video_id: str) -> None:
        if not self._api_token:
            raise RuntimeError("KINESCOPE_API_TOKEN is required for kinescope cleanup")
        vid = (video_id or "").strip()
        if not vid:
            return
        req = Request(
            f"https://api.kinescope.io/v1/videos/{vid}",
            method="DELETE",
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=30) as resp:
                _ = resp.read()
        except HTTPError as exc:
            if exc.code == 404:
                return
            raise RuntimeError(f"Kinescope delete failed with status {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("Kinescope delete network failure") from exc
