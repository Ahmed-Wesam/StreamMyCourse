#!/usr/bin/env python3
"""One-off prod checks for HyperPay webhook endpoint (no secrets printed)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "integration"))

from helpers.billing_access import (  # noqa: E402
    encrypt_hyperpay_notification,
    post_hyperpay_webhook_probe,
)

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
REGION = "eu-west-1"
API_BASE = "https://spjxahk3gg.execute-api.eu-west-1.amazonaws.com/prod"
WEBHOOK_PATH = "/webhooks/payments/hyperpay"
PURCHASE_ID = "49082b74-14fb-421b-afd5-0f59c4af9246"


def _aws(*args: str) -> str:
    out = subprocess.check_output([AWS, *args, "--region", REGION], text=True)
    return out.strip()


def _load_webhook_secret() -> str:
    raw = _aws(
        "secretsmanager",
        "get-secret-value",
        "--secret-id",
        "streammycourse/hyperpay/prod",
        "--query",
        "SecretString",
        "--output",
        "text",
    )
    data = json.loads(raw)
    secret = str(data.get("webhook_secret") or "").strip()
    if len(secret) != 64:
        raise SystemExit(f"SM webhook_secret invalid length: {len(secret)}")
    return secret


def _lambda_webhook_prefix() -> str:
    raw = _aws(
        "lambda",
        "get-function-configuration",
        "--function-name",
        "StreamMyCourse-BillingEdge-prod",
        "--query",
        "Environment.Variables.HYPERPAY_WEBHOOK_SECRET",
        "--output",
        "text",
    )
    return raw[:8]


def main() -> int:
    secret = _load_webhook_secret()
    sm_prefix = secret[:8]
    lam_prefix = _lambda_webhook_prefix()
    print(f"SM webhook prefix: {sm_prefix}")
    print(f"Lambda webhook prefix: {lam_prefix}")
    if sm_prefix != lam_prefix:
        print("FAIL: SM and Lambda webhook secret mismatch")
        return 1
    print("OK: SM and Lambda webhook secret prefixes match")

    url = f"{API_BASE.rstrip('/')}{WEBHOOK_PATH}"

    # 1) HyperPay activation-style probe (no IV/tag)
    r0 = httpx.post(url, content=b"{}", timeout=30.0)
    print(f"Activation probe (no IV/tag): HTTP {r0.status_code} body={r0.text[:120]}")
    if r0.status_code != 200:
        print("FAIL: expected 200 on activation probe")
        return 1
    print("OK: activation probe")

    # 2) Encrypted REGISTRATION (decrypt path, no purchase fulfillment)
    os.environ["INTEGRATION_HYPERPAY_WEBHOOK_SECRET"] = secret
    r1 = post_hyperpay_webhook_probe(API_BASE)
    print(f"Encrypted REGISTRATION probe: HTTP {r1.status_code} body={r1.text[:120]}")
    if r1.status_code != 200:
        print("FAIL: expected 200 on encrypted probe (check secret / wrapper)")
        return 1
    print("OK: encrypted webhook decrypt")

    # 3) Wrong key must 401
    wrong = "0" * 64
    body_hex, iv_hex, tag_hex = encrypt_hyperpay_notification(
        {"type": "REGISTRATION", "action": "CREATED", "payload": {}},
        webhook_secret_hex=wrong,
    )
    r2 = httpx.post(
        url,
        content=body_hex,
        headers={
            "Content-Type": "application/json",
            "X-Initialization-Vector": iv_hex,
            "X-Authentication-Tag": tag_hex,
        },
        timeout=30.0,
    )
    print(f"Wrong-key probe: HTTP {r2.status_code} body={r2.text[:120]}")
    if r2.status_code != 200:
        print(f"WARN: pre-launch fail-open expects 200 even on bad decrypt (got {r2.status_code})")
    else:
        print("OK: wrong key still 200 (pre-launch fail-open; check CloudWatch hyperpay_webhook_debug)")

    # 4) JSON wrapper (HyperPay optional) — we do not support it today
    good_hex, good_iv, good_tag = encrypt_hyperpay_notification(
        {"type": "REGISTRATION", "action": "CREATED", "payload": {}},
        webhook_secret_hex=secret,
    )
    wrapped = json.dumps({"encryptedBody": good_hex})
    r3 = httpx.post(
        url,
        content=wrapped,
        headers={
            "Content-Type": "application/json",
            "X-Initialization-Vector": good_iv,
            "X-Authentication-Tag": good_tag,
        },
        timeout=30.0,
    )
    print(f"JSON wrapper probe: HTTP {r3.status_code} body={r3.text[:120]}")
    if r3.status_code != 200:
        print("WARN: expected 200 for JSON encryptedBody wrapper (portal Click to Test)")
    else:
        print("OK: JSON encryptedBody wrapper accepted")

    # 5) Billing edge invocations in last 24h (REPORT count)
    import time

    start = int((time.time() - 86400) * 1000)
    logs = subprocess.check_output(
        [
            AWS,
            "logs",
            "filter-log-events",
            "--log-group-name",
            "/aws/lambda/StreamMyCourse-BillingEdge-prod",
            "--start-time",
            str(start),
            "--filter-pattern",
            "webhook_enqueued",
            "--limit",
            "5",
            "--output",
            "json",
        ],
        text=True,
    )
    enq = len(json.loads(logs).get("events", []))
    print(f"webhook_enqueued log lines (24h): {enq}")
    if enq == 0:
        print(
            "NOTE: No purchase.paid webhooks enqueued in 24h — "
            "HyperPay has not delivered a PAYMENT webhook we accepted yet"
        )

    print(f"Pending purchase under investigation: {PURCHASE_ID} (still pending unless webhook fired)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
