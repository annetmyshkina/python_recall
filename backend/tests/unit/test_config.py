import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.app_timezone == "UTC"
    assert settings.app_new_cards_per_day == 20
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_settings_accept_valid_iana_timezone() -> None:
    settings = Settings(_env_file=None, app_timezone="Europe/Kirov")

    assert settings.app_timezone == "Europe/Kirov"


def test_settings_reject_invalid_iana_timezone() -> None:
    with pytest.raises(ValidationError, match="valid IANA timezone"):
        Settings(_env_file=None, app_timezone="Mars/Olympus_Mons")


@pytest.mark.parametrize("prefix", ["api/v1", "/api/v1/"])
def test_settings_reject_invalid_api_prefix(prefix: str) -> None:
    with pytest.raises(ValidationError, match="api_v1_prefix"):
        Settings(_env_file=None, api_v1_prefix=prefix)
