import secrets
import time
from dataclasses import dataclass


@dataclass
class Session:
    expires_at: float


class SessionStore:
    def __init__(self, ttl_seconds: int = 8 * 60 * 60):
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}

    def create(self) -> tuple[str, int]:
        self.purge_expired()
        token = secrets.token_urlsafe(32)
        self._sessions[token] = Session(expires_at=time.time() + self.ttl_seconds)
        return token, self.ttl_seconds

    def validate(self, token: str | None) -> bool:
        if not token:
            return False
        session = self._sessions.get(token)
        if session is None:
            return False
        if session.expires_at <= time.time():
            self._sessions.pop(token, None)
            return False
        return True

    def revoke(self, token: str | None) -> None:
        if token:
            self._sessions.pop(token, None)

    def purge_expired(self) -> None:
        now = time.time()
        for token in [key for key, value in self._sessions.items() if value.expires_at <= now]:
            self._sessions.pop(token, None)


def password_matches(provided: str, expected: str) -> bool:
    return bool(expected) and secrets.compare_digest(provided.encode(), expected.encode())
