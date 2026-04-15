from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    tinyfish_api_key: str
    tinyfish_search_url: str = "https://api.search.tinyfish.ai"
    tinyfish_fetch_url: str = "https://api.fetch.tinyfish.ai"
    job_fit_threshold: float = 0.5
    contact_score_threshold: float = 0.4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
