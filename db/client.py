from __future__ import annotations

from typing import Optional

from supabase import Client, create_client

from config import settings

_client: Optional[Client] = None


def get_db() -> Client:
    global _client
    if _client is not None:
        return _client

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY in your environment."
        )

    _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client

