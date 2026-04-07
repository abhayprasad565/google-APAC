"""
L4 — OAuth2 Token Management

Manages OAuth2 access tokens for external services (Google Calendar, Gmail).
Caches access tokens in memory and refreshes them before expiry.
"""

import time
from typing import Optional
import httpx
from command_center.config.settings import settings

# In-memory token cache: service_name -> {token, expires_at}
_token_cache: dict[str, dict] = {}

# Google OAuth2 token endpoint
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Mapping of service names to their refresh tokens from settings
_REFRESH_TOKEN_MAP: dict[str, str] = {
    "google_calendar": "CALENDAR_REFRESH_TOKEN",
    "gmail": "GMAIL_REFRESH_TOKEN",
}


async def get_token(service_name: str) -> str:
    """
    Returns a valid, non-expired OAuth2 access token for the named service.
    Checks cache first; refreshes if expired or missing.
    """
    cached = _token_cache.get(service_name)
    if cached and cached["expires_at"] > time.time() + 60:
        return cached["token"]

    # Get the refresh token from settings
    refresh_token = _get_refresh_token(service_name)
    if not refresh_token:
        raise AuthenticationError(f"No refresh token configured for service: {service_name}")

    # Exchange for a new access token
    token_data = await _exchange_token(
        refresh_token=refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    # Cache the new token
    _token_cache[service_name] = {
        "token": token_data["access_token"],
        "expires_at": time.time() + token_data.get("expires_in", 3600),
    }

    return token_data["access_token"]


def _get_refresh_token(service_name: str) -> Optional[str]:
    """Retrieves the refresh token for a service from settings."""
    attr_name = _REFRESH_TOKEN_MAP.get(service_name)
    if not attr_name:
        return None
    token = getattr(settings, attr_name, "")
    return token if token else None


async def _exchange_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    """
    Exchanges an OAuth2 refresh token for a new access token by calling
    the Google OAuth2 token endpoint.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if response.status_code != 200:
            raise AuthenticationError(
                f"Token exchange failed (HTTP {response.status_code}): {response.text}"
            )
        return response.json()


def clear_cache(service_name: Optional[str] = None) -> None:
    """Clear cached tokens. If service_name is given, clear only that one."""
    if service_name:
        _token_cache.pop(service_name, None)
    else:
        _token_cache.clear()


class AuthenticationError(Exception):
    """Raised when OAuth2 authentication fails."""
    pass
