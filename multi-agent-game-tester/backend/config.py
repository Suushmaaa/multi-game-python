import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    openai_api_key: str = ""

    # Game Configuration
    target_game_url: str = "https://play.ezygamers.com/"

    # Browser Configuration
    chrome_driver_path: str = "auto"
    headless_browser: bool = False

    # Agent Configuration
    max_concurrent_agents: int = 3
    test_timeout: int = 30

    # Output Configuration
    report_output_dir: str = "./reports"
    artifacts_output_dir: str = "./artifacts"

    # Logging
    log_level: str = "INFO"

    # Test Generation
    num_candidate_tests: int = 20
    num_selected_tests: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore unexpected env vars


settings = Settings()

# Create output directories
os.makedirs(settings.report_output_dir, exist_ok=True)
os.makedirs(settings.artifacts_output_dir, exist_ok=True)
