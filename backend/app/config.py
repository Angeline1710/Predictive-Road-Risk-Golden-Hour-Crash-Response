"""Runtime configuration, loaded from environment / .env.

Nothing here is a secret default -- production values come from the
environment, never from this file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RRX_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://rrx:rrx@localhost:5432/rrx"
    redis_url: str = "redis://localhost:6379/0"

    # PRD 11.3: which DispatchGateway implementation to wire up. "simulated"
    # is the only one that exists in v1 -- see app/gateways/.
    gateway: str = "simulated"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 15

    # PRD 6.3.1: crash-alert ingest gets a much higher rate-limit ceiling than
    # everything else, and is never hard-dropped -- excess queues, it doesn't
    # 429. This is the ceiling for OTHER endpoints; /alerts is exempted in code.
    default_rate_limit_per_min: int = 120

    # PRD 10.3: demo-only endpoints (/sim/*). Absent (False) in any build that
    # isn't the hackathon/demo deployment -- the nav item / route doesn't
    # exist, not merely disabled, per UX-APPFLOW.md 25.
    demo_mode: bool = True

    # PRD 6.4: weather/traffic quota discipline. H3 resolution-5 cells are
    # ~250 km^2, which is what makes OpenWeatherMap's ~1000 calls/day tractable.
    h3_resolution: int = 5

    # No keys configured in this deployment -- weather/traffic enrichment
    # legitimately degrades every time (app/services/enrichment.py). Real
    # keys go in .env, never here.
    openweather_api_key: str | None = None
    tomtom_api_key: str | None = None

    log_level: str = "INFO"


settings = Settings()
