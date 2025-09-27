from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    """Application configuration container."""
    default_url: str


def load_config() -> AppConfig:
    """Load configuration values from environment variables or defaults."""
    default_url = os.getenv(
        "SCOREBOARD_API_URL",
        "https://backend.sams-ticker.de/live/indoor/tickers/dvv",
    )
    return AppConfig(default_url=default_url)


CONFIG = load_config()
