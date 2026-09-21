"""AEGIS AI — Rate Limiting & Token Bucket Defense
Implements dual-tier rate limiting (Client IP and Tenant Organization) using
the token-bucket algorithm with sub-second refill resolution.
"""

import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status


@dataclass
class TokenBucket:
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float
    last_update: float

    def consume(self, amount: float = 1.0) -> tuple[bool, float, float]:
        """Attempts to consume `amount` tokens.

        Returns:
            (allowed: bool, remaining_tokens: float, retry_after_seconds: float)
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        self.last_update = now

        # Refill tokens proportional to elapsed time
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))

        if self.tokens >= amount:
            self.tokens -= amount
            return True, self.tokens, 0.0
        else:
            needed = amount - self.tokens
            retry_after = needed / self.refill_rate if self.refill_rate > 0 else 1.0
            return False, self.tokens, round(retry_after, 2)


class RateLimiterRegistry:
    """In-memory rate limiter registry managing IP and Tenant token buckets."""

    def __init__(self):
        self.ip_buckets: dict[str, TokenBucket] = {}
        self.tenant_buckets: dict[str, TokenBucket] = {}

    def get_or_create_bucket(
        self,
        key: str,
        bucket_type: str = "ip",
        capacity: float = 120.0,
        refill_rate: float = 2.0,  # 120 per minute
    ) -> TokenBucket:
        store = self.ip_buckets if bucket_type == "ip" else self.tenant_buckets
        if key not in store:
            store[key] = TokenBucket(
                capacity=capacity,
                refill_rate=refill_rate,
                tokens=capacity,
                last_update=time.monotonic(),
            )
        return store[key]

    def check_rate_limit(
        self,
        key: str,
        bucket_type: str = "ip",
        capacity: float = 120.0,
        refill_rate: float = 2.0,
        cost: float = 1.0,
    ) -> tuple[bool, float, float]:
        """Checks and consumes rate limit quota for key."""
        bucket = self.get_or_create_bucket(key, bucket_type, capacity, refill_rate)
        return bucket.consume(cost)

    def get_status(
        self,
        key: str,
        bucket_type: str = "ip",
        capacity: float = 120.0,
        refill_rate: float = 2.0,
    ) -> dict[str, Any]:
        """Returns current quota status for key without consuming tokens."""
        bucket = self.get_or_create_bucket(key, bucket_type, capacity, refill_rate)
        now = time.monotonic()
        elapsed = now - bucket.last_update
        current_tokens = min(bucket.capacity, bucket.tokens + (elapsed * bucket.refill_rate))
        return {
            "key": key,
            "type": bucket_type,
            "capacity": bucket.capacity,
            "tokens_remaining": round(current_tokens, 2),
            "refill_rate_per_sec": bucket.refill_rate,
            "reset_seconds": round((bucket.capacity - current_tokens) / bucket.refill_rate, 2)
            if bucket.refill_rate > 0 and current_tokens < bucket.capacity
            else 0.0,
        }

    def reset_all(self):
        """Clears all rate limit buckets (useful for test resets)."""
        self.ip_buckets.clear()
        self.tenant_buckets.clear()


# Global Singleton Rate Limiter
rate_limiter = RateLimiterRegistry()


def enforce_rate_limit(
    key: str,
    bucket_type: str = "ip",
    capacity: float = 120.0,
    refill_rate: float = 2.0,
) -> None:
    """Helper to enforce rate limit or raise standard HTTP 429."""
    allowed, remaining, retry_after = rate_limiter.check_rate_limit(
        key=key,
        bucket_type=bucket_type,
        capacity=capacity,
        refill_rate=refill_rate,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {bucket_type}. Retry in {retry_after} seconds.",
            headers={
                "Retry-After": str(int(retry_after) + 1),
                "X-RateLimit-Limit": str(int(capacity)),
                "X-RateLimit-Remaining": str(int(max(0, remaining))),
            },
        )
