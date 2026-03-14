from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    """Application configuration container."""
    default_url: str
    competition_id: str


def load_config() -> AppConfig:
    """Load configuration values from environment variables or defaults."""
    default_url = os.getenv(
        "SCOREBOARD_API_URL",
        "https://backend.sams-ticker.de/live/indoor/tickers/ssvb",
    )
    return AppConfig(default_url=default_url, competition_id="1f559a05-b3af-4dc4-8175-85819c5385e3")


CONFIG = load_config()
