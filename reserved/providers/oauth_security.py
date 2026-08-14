"""Provider-neutral, single-use OAuth state handling."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import MutableMapping


@dataclass(frozen=True)
class OAuthState:
    provider: str
    digest: str
    issued_at: int


class OAuthStateStore:
    """Stores only a hash of a short-lived anti-forgery token.

    The supplied mapping can be a server-side session. A state is bound to one
    provider and is always consumed, including on a failed comparison, which
    prevents replay and repeated guessing.
    """

    KEY = "_reserved_oauth_states"

    def __init__(self, session: MutableMapping, ttl_seconds: int = 600):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.session = session
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def issue(self, provider: str, now: int | None = None) -> str:
        provider = provider.strip().lower()
        if not provider:
            raise ValueError("provider is required")
        raw = secrets.token_urlsafe(32)
        states = dict(self.session.get(self.KEY, {}))
        states[provider] = {"digest": self._digest(raw), "issued_at": int(now or time.time())}
        self.session[self.KEY] = states
        return raw

    def consume(self, provider: str, supplied_state: str | None,
                now: int | None = None) -> bool:
        provider = provider.strip().lower()
        states = dict(self.session.get(self.KEY, {}))
        record = states.pop(provider, None)
        self.session[self.KEY] = states
        if not record or not supplied_state:
            return False
        age = int(now or time.time()) - int(record["issued_at"])
        if age < 0 or age > self.ttl_seconds:
            return False
        return hmac.compare_digest(str(record["digest"]), self._digest(supplied_state))
