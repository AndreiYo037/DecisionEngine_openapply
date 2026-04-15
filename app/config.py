from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    tinyfish_api_key: str
    tinyfish_base_url: str = "https://api.tinyfish.ai"
    tinyfish_search_url: str = "https://api.search.tinyfish.ai"
    match_threshold: int = 70
    contact_threshold: int = 75

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
