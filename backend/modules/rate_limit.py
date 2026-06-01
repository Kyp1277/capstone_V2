import hashlib
import threading
import time

from fastapi import HTTPException


RATE_LIMIT_BUCKETS = {}
RATE_LIMIT_LOCK = threading.Lock()


def rate_limit_key(scope, identifier):
    normalized = str(identifier or "anonymous").strip().lower() or "anonymous"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{scope}:{digest}"


def enforce_rate_limit(scope, identifier, limit=10, window_seconds=60):
    now = time.time()
    key = rate_limit_key(scope, identifier)

    with RATE_LIMIT_LOCK:
        attempts = [
            timestamp
            for timestamp in RATE_LIMIT_BUCKETS.get(key, [])
            if now - timestamp < window_seconds
        ]
        if len(attempts) >= limit:
            RATE_LIMIT_BUCKETS[key] = attempts
            raise HTTPException(
                status_code=429,
                detail="Terlalu banyak percobaan. Tunggu sebentar lalu coba lagi.",
            )
        attempts.append(now)
        RATE_LIMIT_BUCKETS[key] = attempts
