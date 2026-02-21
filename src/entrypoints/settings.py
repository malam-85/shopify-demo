from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    SHOPIFY_SHOP_NAME: str
    SHOPIFY_ACCESS_TOKEN: str
    SHOPIFY_API_VERSION: str = "2025-01"

    EVERSTOX_BASE_URL: str = "https://api.everstox.com"
    EVERSTOX_API_KEY: str


config = Config()  # type: ignore[call-arg]
