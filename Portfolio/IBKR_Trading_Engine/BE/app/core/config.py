from dotenv import load_dotenv, dotenv_values
import os

# loading variables from .env file
load_dotenv()


class Settings:
    user: str = os.getenv("PARTNER")
    trading_env: str = os.getenv("TRADING_ENV")

    env: str = os.getenv("ENV")

    db_env: str = os.getenv("DB_ENV")

    db_host_env: str = os.getenv("DB_HOST")
    if env == "LOCAL":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_LOCAL")
    elif env == "DOCKER":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_DOCKER")
    elif env == "CLOUD":
        IBKR_BASE: str = os.getenv("IBKR_CLIENT_CLOUD")

    DB_CONNECTION: str = os.getenv("DB_CONNECTION")

    DB_PORT: int = os.getenv("DB_PORT")

    if db_host_env == "LOCAL":
        DB_HOST: str = os.getenv("DB_HOST_LOCAL")
        DB_USERNAME: str = os.getenv("DB_USERNAME_LOCAL")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD_LOCAL")
        DB_DATABASE: str = os.getenv("DB_DATABASE_LOCAL")

    elif db_host_env == "CLOUD":
        DB_HOST: str = os.getenv("DB_HOST_CLOUD")
        DB_USERNAME: str = os.getenv("DB_USERNAME_CLOUD")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD_CLOUD")

        if db_env == "PROD":
            DB_DATABASE: str = os.getenv("DB_DATABASE")
        else:
            DB_DATABASE: str = os.getenv("DB_DATABASE_DEV")

    DATABASE_URL = f"{DB_CONNECTION}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    print(DATABASE_URL)


settings = Settings()
