#!/usr/bin/env python3
"""Server-side COPYandPAY payment on eu-test (creates a portal transaction)."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import httpx

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
REGION = "eu-west-1"
SECRET_ID = "streammycourse/hyperpay/prod"


def _sm() -> dict:
    raw = subprocess.check_output(
        [AWS, "secretsmanager", "get-secret-value", "--secret-id", SECRET_ID, "--region", REGION, "--query", "SecretString", "--output", "text"],
        text=True,
    )
    return json.loads(raw)


def _post_form(url: str, fields: list[tuple[str, str]], token: str) -> dict:
    body = urlencode(fields).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("id"):
                return data
        except json.JSONDecodeError:
            pass
        print(f"HTTP {exc.code} from {url}", file=sys.stderr)
        print(raw[:800], file=sys.stderr)
        raise
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("non-object JSON from OPPWA")
    return data


def main() -> int:
    sec = _sm()
    host = str(sec.get("api_host") or "eu-test.oppwa.com").strip()
    entity = str(sec["entity_id"]).strip()
    token = str(sec["access_token"]).strip()
    purchase_id = str(uuid.uuid4())
    user_sub = "s2s-smoke-user"
    merchant_tx = f"v2|prod|{user_sub}|bundle|{purchase_id}"
    amount = "150.00"

    checkout_fields: list[tuple[str, str]] = [
        ("entityId", entity),
        ("amount", amount),
        ("currency", "JOD"),
        ("paymentType", "DB"),
        ("integrity", "true"),
        ("merchantTransactionId", merchant_tx),
        ("shopperResultUrl", "https://dev.researchspectrum.org/billing/result"),
        ("customer.email", "s2s-smoke@noreply.local"),
        ("customer.givenName", "S2S"),
        ("customer.surname", "Smoke"),
        ("billing.street1", "1 Test Street"),
        ("billing.city", "Amman"),
        ("billing.state", "Amman"),
        ("billing.country", "JO"),
        ("billing.postcode", "11118"),
        ("customParameters[SHOPPER_cart]", merchant_tx),
        ("testMode", "EXTERNAL"),
        ("customParameters[3DS2_enrolled]", "true"),
    ]
    checkout_url = f"https://{host}/v1/checkouts"
    checkout = _post_form(checkout_url, checkout_fields, token)
    checkout_id = str(checkout.get("id") or "").strip()
    if not checkout_id:
        print("checkout missing id:", json.dumps(checkout)[:500])
        return 1
    print(f"checkout_id={checkout_id}")
    print(f"merchantTransactionId={merchant_tx}")

    # Server-to-server DB (shows in merchant portal; COPYandPAY checkout payment POST is widget-only).
    pay_fields: list[tuple[str, str]] = [
        ("entityId", entity),
        ("amount", amount),
        ("currency", "JOD"),
        ("paymentType", "DB"),
        ("merchantTransactionId", merchant_tx),
        ("shopperResultUrl", "https://dev.researchspectrum.org/billing/result"),
        ("customer.email", "s2s-smoke@noreply.local"),
        ("customer.givenName", "S2S"),
        ("customer.surname", "Smoke"),
        ("billing.street1", "1 Test Street"),
        ("billing.city", "Amman"),
        ("billing.state", "Amman"),
        ("billing.country", "JO"),
        ("billing.postcode", "11118"),
        ("paymentBrand", "VISA"),
        ("card.number", "4012000033330026"),
        ("card.holder", "Test User"),
        ("card.expiryMonth", "01"),
        ("card.expiryYear", "2039"),
        ("card.cvv", "100"),
        ("testMode", "EXTERNAL"),
        ("customParameters[3DS2_enrolled]", "true"),
    ]
    pay_url = f"https://{host}/v1/payments"
    pay = _post_form(pay_url, pay_fields, token)
    result = pay.get("result") if isinstance(pay.get("result"), dict) else {}
    code = str(result.get("code") or "")
    desc = str(result.get("description") or "")
    payment_id = str(pay.get("id") or "")
    print(f"payment_id={payment_id}")
    print(f"result.code={code}")
    print(f"result.description={desc}")
    if code.startswith("000.000") or code.startswith("000.100.1"):
        print("OK: success result — check merchant portal for this payment id / merchant tx")
        return 0

    redirect = pay.get("redirect") if isinstance(pay.get("redirect"), dict) else {}
    redirect_url = str(redirect.get("url") or "").strip()
    if code.startswith("000.200") and redirect_url:
        print(f"REDIRECT_URL={redirect_url}")
        with httpx.Client(follow_redirects=True, timeout=60.0) as client:
            r = client.post(redirect_url)
            print(f"3DS POST HTTP {r.status_code} final_url={str(r.url)[:160]}")
            if r.status_code >= 400:
                r2 = client.get(redirect_url)
                print(f"3DS GET fallback HTTP {r2.status_code}")
        # Poll payment status
        q = urlencode({"entityId": entity})
        status_url = f"https://{host}/v1/payments/{payment_id}?{q}"
        status_req = Request(status_url, headers={"Authorization": f"Bearer {token}"})
        with urlopen(status_req, timeout=30) as resp:
            final = json.loads(resp.read().decode())
        result2 = final.get("result") if isinstance(final.get("result"), dict) else {}
        code2 = str(result2.get("code") or "")
        print(f"after_3ds result.code={code2}")
        if code2.startswith("000.000") or code2.startswith("000.100.1"):
            print("OK: success after 3DS — check merchant portal")
            return 0

    if redirect_url:
        print("portal: search merchant portal for payment_id and merchantTransactionId above (may show as 3D/pending until 3DS completes)")
    print(json.dumps(pay, indent=2)[:2000])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
