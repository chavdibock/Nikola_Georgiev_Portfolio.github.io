from dotenv import load_dotenv, dotenv_values
import os

# loading variables from .env file
load_dotenv()


class Settings:
    user: str = os.getenv("PARTNER")
    trading_env: str = os.getenv("TRADING_ENV")

    client: str = os.getenv("CLIENT")

    db_env: str = os.getenv("DB_ENV")

    if user == "NIKOLA":
        if trading_env == "PAPER":
            IBKR_USER: str = os.getenv("IBKR_ACC_PAPER_NIKOLA")
        else:
            IBKR_USER: str = os.getenv("IBKR_ACC_NIKOLA")
    elif user == "MISHO":
        if trading_env == "PAPER":
            IBKR_USER: str = os.getenv("IBKR_ACC_PAPER_MISHO")
        else:
            IBKR_USER: str = os.getenv("IBKR_ACC_MISHO")

    if client is None:
        ibkr_client: str = os.getenv("IBKR_CLIENT_LOCAL")
    elif client == "DOCKER":
        ibkr_client: str = os.getenv("IBKR_CLIENT_DOCKER")
    elif client == "CLOUD":
        ibkr_client: str = os.getenv("IBKR_CLIENT_CLOUD")

    DB_CONNECTION: str = os.getenv("DB_CONNECTION")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = os.getenv("DB_PORT")
    DB_USERNAME: str = os.getenv("DB_USERNAME")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")

    if db_env == "PROD":
        DB_DATABASE: str = os.getenv("DB_DATABASE")
    else:
        DB_DATABASE: str = os.getenv("DB_DATABASE_DEV")

    DATABASE_URL = f"{DB_CONNECTION}://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"


settings = Settings()
