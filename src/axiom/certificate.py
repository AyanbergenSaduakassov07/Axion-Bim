"""Content hash of a frozen acceptance certificate (D-42).

A SHA-256 over canonical JSON shows that a stored certificate was not edited after issue. It is not a
cryptographic signature: there is no key, so it does not prove who issued it. That needs users (G11).
"""

from __future__ import annotations

import hashlib
import hmac
import json


def digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify(payload: dict, sha256: str) -> bool:
    return hmac.compare_digest(digest(payload), sha256)
